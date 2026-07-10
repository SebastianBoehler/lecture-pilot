from __future__ import annotations

import re
from pathlib import Path

from lecturepilot.canvas_workspace_config import SEEDED_COURSE_ID, lecture_source_name
from lecturepilot.latex_canvas_text import BROWSER_ASSET_SUFFIXES, is_allowed_canvas_asset
from lecturepilot.pdf_preview import PdfPreviewError, render_pdf_preview
from lecturepilot.storage_layout import StorageLayout
from lecturepilot.workspace_capability import CapabilityRoot, WorkspaceCapability
from lecturepilot.workspace_fs import WorkspaceFS, WorkspaceFSError


COURSE_MEDIA_SUFFIXES = BROWSER_ASSET_SUFFIXES | {".mp4", ".webm", ".mov", ".mkv", ".avi"}
MAX_COURSE_MEDIA_BYTES = 500 * 1024 * 1024


class CanvasAssetError(RuntimeError):
    """Raised when a course or learner canvas asset cannot be served."""


class CanvasAssetStore:
    def __init__(self, *, layout: StorageLayout, material_root: Path) -> None:
        self.layout = layout
        self.material_root = material_root

    def course_asset_path(self, *, course_id: str, lecture_id: str, asset_path: str) -> Path:
        _assert_safe_asset_path(asset_path, "course material root", COURSE_MEDIA_SUFFIXES)
        candidates = [
            (self.layout.course_normalized_dir(course_id), asset_path),
            (self.layout.course_uploads_dir(course_id), asset_path),
            (self.layout.course_uploads_dir(course_id), f"images/{asset_path}"),
            (self.material_root, f"images/{asset_path}"),
        ]
        if source := self._maybe_source_path(course_id, lecture_id):
            candidates.insert(0, (source.parent, asset_path))
        for root, relative in candidates:
            candidate = _safe_candidate(root, relative)
            if candidate is None:
                continue
            if _is_allowed_course_media(candidate):
                return candidate
        raise CanvasAssetError("Canvas asset was not found.")

    def course_asset_preview_path(self, *, course_id: str, lecture_id: str, asset_path: str) -> Path:
        source = self.course_asset_path(course_id=course_id, lecture_id=lecture_id, asset_path=asset_path)
        if source.suffix.lower() != ".pdf":
            return source
        try:
            return render_pdf_preview(source, self.layout.root / "cache" / "pdf-previews")
        except PdfPreviewError as exc:
            raise CanvasAssetError(str(exc)) from exc

    def workspace_asset_path(
        self,
        *,
        course_id: str,
        lecture_id: str,
        student_key: str,
        asset_path: str,
    ) -> Path:
        if not re.fullmatch(r"[a-f0-9]{24}", student_key):
            raise CanvasAssetError("Workspace asset user key is invalid.")
        _assert_safe_asset_path(asset_path, "learner workspace", BROWSER_ASSET_SUFFIXES)
        candidates = [
            (self.layout.user_canvas_dir_by_key(student_key, course_id, lecture_id), asset_path),
            (self.layout.legacy_canvas_dir_by_key(student_key, course_id, lecture_id), asset_path),
        ]
        for root, relative in candidates:
            candidate = _safe_candidate(root, relative)
            if candidate is None:
                continue
            if is_allowed_canvas_asset(candidate):
                return candidate
        raise CanvasAssetError("Workspace asset was not found.")

    def _source_path(self, course_id: str, lecture_id: str) -> Path:
        source_name = lecture_source_name(lecture_id)
        uploads_dir = self.layout.course_uploads_dir(course_id)
        source_names = [source_name] if source_name else []
        if uploads_dir.exists():
            workspace = WorkspaceFS(
                WorkspaceCapability((CapabilityRoot("/uploads", uploads_dir),))
            )
            source_names.extend(
                item.logical.removeprefix("/uploads/")
                for item in workspace.files("/uploads")
                if item.path.suffix.lower() == ".tex"
            )
        candidates = [uploads_dir / name for name in dict.fromkeys(source_names)]
        if source_name and course_id == SEEDED_COURSE_ID:
            candidates.append(self.material_root / source_name)
        for source_path in candidates:
            source = _safe_candidate(source_path.parent, source_path.name)
            if source is not None and source.is_file():
                return source
        raise CanvasAssetError(f"No LaTeX source found for {course_id}/{lecture_id}.")

    def _maybe_source_path(self, course_id: str, lecture_id: str) -> Path | None:
        try:
            return self._source_path(course_id, lecture_id)
        except CanvasAssetError:
            return None


def _assert_safe_asset_path(asset_path: str, label: str, suffixes: set[str]) -> None:
    if ".." in Path(asset_path).parts or asset_path.startswith("/"):
        raise CanvasAssetError(f"Asset path must stay inside {label}.")
    if Path(asset_path).suffix.lower() not in suffixes:
        raise CanvasAssetError("Canvas assets are limited to supported media files.")


def _is_allowed_course_media(path: Path) -> bool:
    return (
        path.is_file()
        and path.suffix.lower() in COURSE_MEDIA_SUFFIXES
        and path.stat().st_size <= MAX_COURSE_MEDIA_BYTES
    )


def _safe_candidate(root: Path, relative: str) -> Path | None:
    if not root.exists():
        return None
    try:
        workspace = WorkspaceFS(
            WorkspaceCapability((CapabilityRoot("/asset", root, writable=False),))
        )
        return workspace.resolve(f"/asset/{relative}").path
    except (FileNotFoundError, WorkspaceFSError):
        return None
