from __future__ import annotations

import json
import re
from hashlib import sha256
from pathlib import Path

from lecturepilot.canvas_models import CanvasDocument, CanvasSection
from lecturepilot.canvas_markdown import (
    read_document_source,
    write_document_source,
    write_student_sections,
)
from lecturepilot.canvas_sections import merge_sections
from lecturepilot.canvas_workspace_config import (
    default_material_root as _default_material_root,
    default_workspace_root as _default_workspace_root,
    lecture_source_name,
)
from lecturepilot.course_canvas_store import CourseCanvasStore
from lecturepilot.course_media import apply_course_media
from lecturepilot.generated_infographics import materialize_infographic_sections
from lecturepilot.latex_canvas_importer import CANVAS_IMPORT_VERSION, import_latex_canvas
from lecturepilot.latex_canvas_text import (
    BROWSER_ASSET_SUFFIXES,
    is_allowed_canvas_asset,
)
from lecturepilot.pdf_preview import PdfPreviewError, render_pdf_preview


class CanvasWorkspaceError(RuntimeError):
    """Raised when course canvas material cannot be loaded safely."""


class CanvasWorkspace:
    def __init__(
        self,
        *,
        workspace_root: Path | None = None,
        material_root: Path | None = None,
    ) -> None:
        self.workspace_root = workspace_root or _default_workspace_root()
        self.material_root = material_root or _default_material_root()
        self.course_canvas_store = CourseCanvasStore(self.material_root)

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
        student_key = _pseudonymous_id(user_id)
        canvas_dir = self._canvas_dir(course_id, lecture_id, user_id)
        return materialize_infographic_sections(
            sections=sections,
            prompt=prompt,
            asset_dir=canvas_dir / "student-assets",
            asset_url_prefix=(
                f"/workspace-assets/{_safe_id(course_id)}/{_safe_id(lecture_id)}/"
                f"{student_key}/student-assets"
            ),
            image_generator=getattr(self, "image_generator", None),
        )

    def asset_path(self, *, lecture_id: str, asset_path: str) -> Path:
        if ".." in Path(asset_path).parts or asset_path.startswith("/"):
            raise CanvasWorkspaceError("Asset path must stay inside course material root.")
        if Path(asset_path).suffix.lower() not in BROWSER_ASSET_SUFFIXES:
            raise CanvasWorkspaceError("Canvas assets are limited to browser-renderable course files.")
        source = self._source_path(lecture_id)
        candidate = source.parent / asset_path
        if is_allowed_canvas_asset(candidate):
            return candidate
        image_candidate = self.material_root / "images" / asset_path
        if is_allowed_canvas_asset(image_candidate):
            return image_candidate
        raise CanvasWorkspaceError("Canvas asset was not found.")

    def asset_preview_path(self, *, lecture_id: str, asset_path: str) -> Path:
        source = self.asset_path(lecture_id=lecture_id, asset_path=asset_path)
        if source.suffix.lower() != ".pdf":
            return source
        try:
            return render_pdf_preview(source, self.material_root / ".lecturepilot-previews")
        except PdfPreviewError as exc:
            raise CanvasWorkspaceError(str(exc)) from exc

    def workspace_asset_path(
        self,
        *,
        course_id: str,
        lecture_id: str,
        student_key: str,
        asset_path: str,
    ) -> Path:
        if not re.fullmatch(r"[a-f0-9]{24}", student_key):
            raise CanvasWorkspaceError("Workspace asset user key is invalid.")
        if ".." in Path(asset_path).parts or asset_path.startswith("/"):
            raise CanvasWorkspaceError("Asset path must stay inside learner workspace.")
        if Path(asset_path).suffix.lower() not in BROWSER_ASSET_SUFFIXES:
            raise CanvasWorkspaceError("Workspace assets are limited to browser-renderable files.")
        root = (
            self.workspace_root
            / "students"
            / student_key
            / "courses"
            / _safe_id(course_id)
            / "lectures"
            / _safe_id(lecture_id)
            / "canvas"
        )
        candidate = root / asset_path
        if not is_allowed_canvas_asset(candidate):
            raise CanvasWorkspaceError("Workspace asset was not found.")
        return candidate

    def _initial_document(self, *, course_id: str, lecture_id: str, user_id: str) -> CanvasDocument:
        canvas_dir = self._canvas_dir(course_id, lecture_id, user_id)
        if base_document := self.course_canvas_store.read(
            course_id=course_id,
            lecture_id=lecture_id,
            workspace_path=str(canvas_dir / "index.md"),
        ):
            return base_document
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
        source_path = self._source_path(lecture_id)
        return import_latex_canvas(
            source_path=source_path,
            material_root=self.material_root,
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
        return base is not None and document.source_kind != "generated"

    def write_course_canvas(self, document: CanvasDocument) -> CanvasDocument:
        return self.course_canvas_store.write(document)

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
                section for section in read_document_source(canvas_dir).sections if _is_student_section(section)
            )
        compiled_path = self._compiled_path(course_id, lecture_id, user_id)
        if compiled_path.exists():
            payload = json.loads(compiled_path.read_text(encoding="utf-8"))
            sections.extend(
                section
                for section in CanvasDocument.model_validate(payload).sections
                if _is_student_section(section)
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
        base_sections = [section for section in document.sections if not _is_student_section(section)]
        student_sections = [section for section in document.sections if _is_student_section(section)]
        sections_dir = canvas_dir / "sections"
        if sections_dir.exists():
            for path in sections_dir.glob("*.md"):
                path.unlink()
        write_document_source(document.model_copy(update={"sections": base_sections}), canvas_dir)
        if student_sections:
            write_student_sections(canvas_dir, student_sections)

    def _lecture_workspace_dir(self, course_id: str, lecture_id: str, user_id: str) -> Path:
        return (
            self.workspace_root
            / "students"
            / _pseudonymous_id(user_id)
            / "courses"
            / _safe_id(course_id)
            / "lectures"
            / _safe_id(lecture_id)
        )

    def _canvas_dir(self, course_id: str, lecture_id: str, user_id: str) -> Path:
        return self._lecture_workspace_dir(course_id, lecture_id, user_id) / "canvas"

    def _compiled_path(self, course_id: str, lecture_id: str, user_id: str) -> Path:
        return self._lecture_workspace_dir(course_id, lecture_id, user_id) / "canvas.json"

    def _source_path(self, lecture_id: str) -> Path:
        source_name = lecture_source_name(lecture_id)
        if source_name is None:
            raise CanvasWorkspaceError(f"No source mapping configured for {lecture_id}.")
        source_path = self.material_root / source_name
        if not source_path.exists():
            raise CanvasWorkspaceError(f"Course source not found: {source_path}")
        return source_path


def _safe_id(value: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "-", value).strip("-")
    if not safe:
        raise CanvasWorkspaceError("Workspace id cannot be empty.")
    return safe[:120]


def _pseudonymous_id(user_id: str) -> str:
    return sha256(user_id.encode("utf-8")).hexdigest()[:24]


def _is_student_section(section: CanvasSection) -> bool:
    return section.source_ref == "student workspace" or section.id.startswith("student-")
