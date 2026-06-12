from __future__ import annotations

import json
from pathlib import Path

from lecturepilot.canvas_models import CanvasDocument, CanvasSection
from lecturepilot.canvas_asset_store import CanvasAssetError, CanvasAssetStore
from lecturepilot.canvas_markdown import (
    read_document_source,
    write_document_source,
    write_student_sections,
)
from lecturepilot.canvas_sections import merge_sections
from lecturepilot.canvas_signatures import official_canvas_signature, is_student_section
from lecturepilot.canvas_workspace_config import (
    default_material_root as _default_material_root,
    default_workspace_root as _default_workspace_root,
    lecture_source_name,
    SEEDED_COURSE_ID,
)
from lecturepilot.course_canvas_store import CourseCanvasStore
from lecturepilot.course_media import apply_course_media
from lecturepilot.generated_infographics import materialize_infographic_sections
from lecturepilot.latex_canvas_importer import CANVAS_IMPORT_VERSION, import_latex_canvas
from lecturepilot.storage_layout import DEFAULT_TENANT_ID, StorageLayout, safe_id


class CanvasWorkspaceError(RuntimeError):
    """Raised when course canvas material cannot be loaded safely."""


class CanvasWorkspace:
    def __init__(
        self,
        *,
        workspace_root: Path | None = None,
        material_root: Path | None = None,
        tenant_id: str = DEFAULT_TENANT_ID,
    ) -> None:
        self.workspace_root = workspace_root or _default_workspace_root()
        self.material_root = material_root or _default_material_root()
        self.layout = StorageLayout(self.workspace_root, tenant_id=tenant_id)
        self.course_canvas_store = CourseCanvasStore(
            self.layout,
            legacy_material_root=self.material_root,
        )
        self.asset_store = CanvasAssetStore(layout=self.layout, material_root=self.material_root)

    def read_document(
        self,
        *,
        course_id: str,
        lecture_id: str,
        user_id: str,
    ) -> CanvasDocument:
        canvas_dir = self._canvas_dir(course_id, lecture_id, user_id)
        manifest_path = canvas_dir / "index.md"
        if not manifest_path.exists() or self._is_stale_canvas_manifest(manifest_path):
            student_sections = self._read_student_sections(
                course_id=course_id,
                lecture_id=lecture_id,
                user_id=user_id,
                canvas_dir=canvas_dir,
            )
            document = self._initial_document(
                course_id=course_id,
                lecture_id=lecture_id,
                user_id=user_id,
            )
            if student_sections:
                document = document.model_copy(
                    update={"sections": merge_sections([*document.sections, *student_sections])}
                )
            self._write_initial_source(document, canvas_dir)

        document = apply_course_media(read_document_source(canvas_dir), self.material_root)
        document = apply_course_media(document, self.course_media_root(course_id))
        self._write_compiled_document(document, course_id, lecture_id, user_id)
        return document

    def apply_sections(
        self,
        *,
        course_id: str,
        lecture_id: str,
        user_id: str,
        sections: list[CanvasSection],
    ) -> CanvasDocument:
        document = self.read_document(course_id=course_id, lecture_id=lecture_id, user_id=user_id)
        write_student_sections(Path(document.workspace_path).parent, sections)
        document = read_document_source(Path(document.workspace_path).parent)
        self._write_compiled_document(document, course_id, lecture_id, user_id)
        return document

    def prepare_generated_sections(
        self,
        *,
        course_id: str,
        lecture_id: str,
        user_id: str,
        prompt: str,
        sections: list[CanvasSection],
    ) -> list[CanvasSection]:
        student_key = self.layout.user_key(user_id)
        canvas_dir = self._canvas_dir(course_id, lecture_id, user_id)
        return materialize_infographic_sections(
            sections=sections,
            prompt=prompt,
            asset_dir=canvas_dir / "student-assets",
            asset_url_prefix=(
                f"/workspace-assets/{safe_id(course_id)}/{safe_id(lecture_id)}/"
                f"{student_key}/student-assets"
            ),
            image_generator=getattr(self, "image_generator", None),
        )

    def asset_path(
        self,
        *,
        course_id: str,
        lecture_id: str,
        asset_path: str,
    ) -> Path:
        try:
            return self.asset_store.course_asset_path(
                course_id=course_id,
                lecture_id=lecture_id,
                asset_path=asset_path,
            )
        except CanvasAssetError as exc:
            raise CanvasWorkspaceError(str(exc)) from exc

    def asset_preview_path(
        self,
        *,
        course_id: str,
        lecture_id: str,
        asset_path: str,
    ) -> Path:
        try:
            return self.asset_store.course_asset_preview_path(
                course_id=course_id,
                lecture_id=lecture_id,
                asset_path=asset_path,
            )
        except CanvasAssetError as exc:
            raise CanvasWorkspaceError(str(exc)) from exc

    def workspace_asset_path(
        self,
        *,
        course_id: str,
        lecture_id: str,
        student_key: str,
        asset_path: str,
    ) -> Path:
        try:
            return self.asset_store.workspace_asset_path(
                course_id=course_id,
                lecture_id=lecture_id,
                student_key=student_key,
                asset_path=asset_path,
            )
        except CanvasAssetError as exc:
            raise CanvasWorkspaceError(str(exc)) from exc

    def course_upload_path(self, *, course_id: str, path: str) -> Path:
        if ".." in Path(path).parts or path.startswith("/"):
            raise CanvasWorkspaceError("Course source path must stay inside source uploads.")
        return self.layout.course_uploads_dir(course_id) / path

    def course_media_root(self, course_id: str) -> Path:
        return self.layout.course_root(course_id)

    def source_bundle_roots(self, course_id: str, *, include_seeded_materials: bool = True) -> list[Path]:
        roots = [self.layout.course_uploads_dir(course_id)]
        if include_seeded_materials:
            roots.append(self.material_root)
        return [root for index, root in enumerate(roots) if root.exists() and root not in roots[:index]]

    def _initial_document(self, *, course_id: str, lecture_id: str, user_id: str) -> CanvasDocument:
        canvas_dir = self._canvas_dir(course_id, lecture_id, user_id)
        if base_document := self.course_canvas_store.read(
            course_id=course_id,
            lecture_id=lecture_id,
            workspace_path=str(canvas_dir / "index.md"),
        ):
            return base_document
        if self._has_course_uploads(course_id):
            raise CanvasWorkspaceError("Canvas has not been published.")
        return self.source_document(
            course_id=course_id,
            lecture_id=lecture_id,
            workspace_path=str(canvas_dir / "index.md"),
        )

    def source_document(
        self,
        *,
        course_id: str,
        lecture_id: str,
        workspace_path: str,
    ) -> CanvasDocument:
        source_path = self._source_path(course_id, lecture_id)
        return import_latex_canvas(
            source_path=source_path,
            material_root=source_path.parent,
            course_id=course_id,
            lecture_id=lecture_id,
            workspace_path=workspace_path,
        )

    def _is_stale_canvas_manifest(self, manifest_path: Path) -> bool:
        document = read_document_source(manifest_path.parent)
        if document.import_version != CANVAS_IMPORT_VERSION:
            return True
        base = self.course_canvas_store.read(
            course_id=document.course_id,
            lecture_id=document.lecture_id,
            workspace_path=document.workspace_path,
        )
        if base is None:
            return False
        if document.source_kind != "generated":
            return True
        return official_canvas_signature(document) != official_canvas_signature(base)

    def write_course_canvas(self, document: CanvasDocument) -> CanvasDocument:
        return self.course_canvas_store.write(document)

    def read_course_canvas_draft(self, *, course_id: str, lecture_id: str) -> CanvasDocument:
        document = self.course_canvas_store.read_draft(course_id=course_id, lecture_id=lecture_id)
        if document is None:
            raise CanvasWorkspaceError("No canvas draft exists for this lecture.")
        document = apply_course_media(document, self.material_root)
        return apply_course_media(document, self.course_media_root(course_id))

    def write_course_canvas_draft(self, document: CanvasDocument) -> CanvasDocument:
        return self.course_canvas_store.write_draft(document)

    def publish_course_canvas_draft(
        self,
        *,
        course_id: str,
        lecture_id: str,
        published_by: str,
    ) -> dict:
        try:
            return self.course_canvas_store.publish_draft(
                course_id=course_id,
                lecture_id=lecture_id,
                published_by=published_by,
            )
        except FileNotFoundError as exc:
            raise CanvasWorkspaceError(str(exc)) from exc

    def course_canvas_publication(self, *, course_id: str, lecture_id: str) -> dict | None:
        return self.course_canvas_store.publication(course_id=course_id, lecture_id=lecture_id)

    def has_published_course_canvas(self, *, course_id: str, lecture_id: str) -> bool:
        return (self.course_canvas_store.path(course_id, lecture_id) / "index.md").exists()

    def _read_student_sections(
        self,
        *,
        course_id: str,
        lecture_id: str,
        user_id: str,
        canvas_dir: Path,
    ) -> list[CanvasSection]:
        sections: list[CanvasSection] = []
        if (canvas_dir / "index.md").exists():
            sections.extend(
                section for section in read_document_source(canvas_dir).sections if is_student_section(section)
            )
        compiled_paths = [
            self._compiled_path(course_id, lecture_id, user_id),
            self.layout.legacy_compiled_canvas_path(user_id, course_id, lecture_id),
        ]
        for compiled_path in compiled_paths:
            if not compiled_path.exists():
                continue
            payload = json.loads(compiled_path.read_text(encoding="utf-8"))
            sections.extend(
                section
                for section in CanvasDocument.model_validate(payload).sections
                if is_student_section(section)
            )
        return merge_sections(sections)

    def _write_compiled_document(
        self,
        document: CanvasDocument,
        course_id: str,
        lecture_id: str,
        user_id: str,
    ) -> None:
        path = self._compiled_path(course_id, lecture_id, user_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(document.model_dump(), indent=2), encoding="utf-8")

    def _write_initial_source(self, document: CanvasDocument, canvas_dir: Path) -> None:
        base_sections = [section for section in document.sections if not is_student_section(section)]
        student_sections = [section for section in document.sections if is_student_section(section)]
        sections_dir = canvas_dir / "sections"
        if sections_dir.exists():
            for path in sections_dir.glob("*.md"):
                path.unlink()
        write_document_source(document.model_copy(update={"sections": base_sections}), canvas_dir)
        if student_sections:
            write_student_sections(canvas_dir, student_sections)

    def _lecture_workspace_dir(self, course_id: str, lecture_id: str, user_id: str) -> Path:
        return self.layout.user_lecture_root(user_id, course_id, lecture_id)

    def _canvas_dir(self, course_id: str, lecture_id: str, user_id: str) -> Path:
        return self._lecture_workspace_dir(course_id, lecture_id, user_id) / "canvas"

    def _compiled_path(self, course_id: str, lecture_id: str, user_id: str) -> Path:
        return self._lecture_workspace_dir(course_id, lecture_id, user_id) / "canvas.json"

    def _source_path(self, course_id: str, lecture_id: str) -> Path:
        source_name = lecture_source_name(lecture_id)
        uploads_dir = self.layout.course_uploads_dir(course_id)
        source_names = [source_name] if source_name else []
        source_names.extend(str(path.relative_to(uploads_dir)) for path in sorted(uploads_dir.rglob("*.tex")))
        candidates = [uploads_dir / name for name in dict.fromkeys(source_names)]
        if source_name and course_id == SEEDED_COURSE_ID:
            candidates.append(self.material_root / source_name)
        for source_path in candidates:
            if source_path.exists():
                return source_path
        raise CanvasWorkspaceError(f"No LaTeX source found for {course_id}/{lecture_id}.")

    def _has_course_uploads(self, course_id: str) -> bool:
        uploads_dir = self.layout.course_uploads_dir(course_id)
        return uploads_dir.exists() and any(path.is_file() for path in uploads_dir.rglob("*"))
