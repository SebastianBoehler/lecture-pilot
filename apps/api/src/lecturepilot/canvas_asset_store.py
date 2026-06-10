from __future__ import annotations

import re
from pathlib import Path

from lecturepilot.canvas_workspace_config import lecture_source_name
from lecturepilot.latex_canvas_text import BROWSER_ASSET_SUFFIXES, is_allowed_canvas_asset
from lecturepilot.pdf_preview import PdfPreviewError, render_pdf_preview
from lecturepilot.storage_layout import StorageLayout


class CanvasAssetError(RuntimeError):
    """Raised when a course or learner canvas asset cannot be served."""


class CanvasAssetStore:
    def __init__(self, *, layout: StorageLayout, material_root: Path) -> None:
        self.layout = layout
        self.material_root = material_root

    def course_asset_path(self, *, course_id: str, lecture_id: str, asset_path: str) -> Path:
        _assert_safe_asset_path(asset_path, "course material root")
        source = self._source_path(course_id, lecture_id)
        candidates = [
            source.parent / asset_path,
            self.layout.course_uploads_dir(course_id) / "images" / asset_path,
            self.material_root / "images" / asset_path,
        ]
        for candidate in candidates:
            if is_allowed_canvas_asset(candidate):
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
        _assert_safe_asset_path(asset_path, "learner workspace")
        candidates = [
            self.layout.user_canvas_dir_by_key(student_key, course_id, lecture_id) / asset_path,
            self.layout.legacy_canvas_dir_by_key(student_key, course_id, lecture_id) / asset_path,
        ]
        for candidate in candidates:
            if is_allowed_canvas_asset(candidate):
                return candidate
        raise CanvasAssetError("Workspace asset was not found.")

    def _source_path(self, course_id: str, lecture_id: str) -> Path:
        source_name = lecture_source_name(lecture_id)
        if source_name is None:
            raise CanvasAssetError(f"No source mapping configured for {lecture_id}.")
        candidates = [
            self.layout.course_uploads_dir(course_id) / source_name,
            self.material_root / source_name,
        ]
        for source_path in candidates:
            if source_path.exists():
                return source_path
        raise CanvasAssetError(f"Course source not found: {candidates[-1]}")


def _assert_safe_asset_path(asset_path: str, label: str) -> None:
    if ".." in Path(asset_path).parts or asset_path.startswith("/"):
        raise CanvasAssetError(f"Asset path must stay inside {label}.")
    if Path(asset_path).suffix.lower() not in BROWSER_ASSET_SUFFIXES:
        raise CanvasAssetError("Canvas assets are limited to browser-renderable files.")
