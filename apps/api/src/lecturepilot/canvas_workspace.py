from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from lecturepilot.canvas_models import CanvasDocument, CanvasSection
from lecturepilot.canvas_learner_workspace import CanvasLearnerWorkspaceMixin
from lecturepilot.canvas_asset_store import CanvasAssetError, CanvasAssetStore
from lecturepilot.canvas_learning_support import normalize_learning_support
from lecturepilot.canvas_workspace_config import (
    default_material_root as _default_material_root,
    default_workspace_root as _default_workspace_root,
    lecture_source_name,
    SEEDED_COURSE_ID,
)
from lecturepilot.course_canvas_store import CourseCanvasStore
from lecturepilot.course_canvas_context import PublishedCanvasSnapshot
from lecturepilot.course_update_recovery import locked_course_state
from lecturepilot.course_media import apply_course_media
from lecturepilot.generated_infographics import materialize_infographic_sections
from lecturepilot.latex_canvas_importer import import_latex_canvas
from lecturepilot.lecture_source_selection import lecture_source_candidates
from lecturepilot.storage_layout import DEFAULT_TENANT_ID, StorageLayout, safe_id
from lecturepilot.safe_course_files import safe_files, safe_path
from lecturepilot.workspace_fs import WorkspaceFSError


class CanvasWorkspaceError(RuntimeError):
    """Raised when course canvas material cannot be loaded safely."""


class CanvasWorkspace(CanvasLearnerWorkspaceMixin):
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

    def source_bundle_roots(
        self, course_id: str, *, include_seeded_materials: bool = True
    ) -> list[Path]:
        roots = [self.layout.course_uploads_dir(course_id)]
        if include_seeded_materials:
            roots.append(self.material_root)
        return [
            root for index, root in enumerate(roots) if root.exists() and root not in roots[:index]
        ]

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

    def write_course_canvas(self, document: CanvasDocument) -> CanvasDocument:
        return self.course_canvas_store.write(document)

    def read_published_canvas_view(
        self,
        *,
        course_id: str,
        lecture_id: str,
        user_id: str,
    ) -> PublishedCanvasSnapshot | None:
        snapshot = self.course_canvas_store.read_current_published_snapshot(
            course_id=course_id,
            lecture_id=lecture_id,
        )
        if snapshot is None:
            return None
        document = self.read_published_document(
            snapshot.document,
            course_id=course_id,
            lecture_id=lecture_id,
            user_id=user_id,
        )
        return replace(snapshot, document=document)

    def read_course_canvas_draft(self, *, course_id: str, lecture_id: str) -> CanvasDocument:
        document = self.course_canvas_store.read_draft(course_id=course_id, lecture_id=lecture_id)
        if document is None:
            raise CanvasWorkspaceError("No canvas draft exists for this lecture.")
        document = apply_course_media(normalize_learning_support(document), self.material_root)
        return apply_course_media(document, self.course_media_root(course_id))

    def write_course_canvas_draft(
        self,
        document: CanvasDocument,
        *,
        expected_source_revision: str | None = None,
    ) -> CanvasDocument:
        return self.course_canvas_store.write_draft(
            document,
            expected_source_revision=expected_source_revision,
        )

    def publish_course_canvas_draft(
        self,
        *,
        course_id: str,
        lecture_id: str,
        published_by: str,
    ) -> dict:
        try:
            with locked_course_state(self.course_media_root(course_id)):
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

    def _source_path(self, course_id: str, lecture_id: str) -> Path:
        source_name = lecture_source_name(lecture_id)
        uploads_dir = self.layout.course_uploads_dir(course_id)
        try:
            uploaded_sources = safe_files(uploads_dir, suffix=".tex")
        except WorkspaceFSError as exc:
            raise CanvasWorkspaceError("Course source contains an unsafe symbolic link.") from exc
        candidates = lecture_source_candidates(
            lecture_id=lecture_id,
            uploads_dir=uploads_dir,
            uploaded_sources=uploaded_sources,
            configured_source=source_name,
        )
        if source_name and course_id == SEEDED_COURSE_ID:
            candidates.append(self.material_root / source_name)
        for source_path in candidates:
            for root in (uploads_dir, self.material_root):
                if candidate := safe_path(root, source_path):
                    return candidate
        raise CanvasWorkspaceError(f"No LaTeX source found for {course_id}/{lecture_id}.")

    def _has_course_uploads(self, course_id: str) -> bool:
        uploads_dir = self.layout.course_uploads_dir(course_id)
        try:
            return bool(safe_files(uploads_dir))
        except WorkspaceFSError as exc:
            raise CanvasWorkspaceError("Course source contains an unsafe symbolic link.") from exc
