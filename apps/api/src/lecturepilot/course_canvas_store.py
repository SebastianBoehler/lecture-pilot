from __future__ import annotations

import re
from pathlib import Path

from lecturepilot.canvas_markdown import read_document_source, write_document_source
from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.storage_layout import StorageLayout


class CourseCanvasStore:
    def __init__(self, layout: StorageLayout, *, legacy_material_root: Path | None = None) -> None:
        self.layout = layout
        self.legacy_material_root = legacy_material_root

    def read(
        self,
        *,
        course_id: str,
        lecture_id: str,
        workspace_path: str,
    ) -> CanvasDocument | None:
        canvas_dir = self._read_path(course_id, lecture_id)
        if canvas_dir is None:
            return None
        return read_document_source(canvas_dir).model_copy(update={"workspace_path": workspace_path})

    def write(self, document: CanvasDocument) -> CanvasDocument:
        canvas_dir = self.path(document.course_id, document.lecture_id)
        _clear_sections(canvas_dir)
        write_document_source(
            document.model_copy(update={"workspace_path": str(canvas_dir / "index.md")}),
            canvas_dir,
        )
        return read_document_source(canvas_dir)

    def path(self, course_id: str, lecture_id: str) -> Path:
        return self.layout.course_canvas_dir(course_id, lecture_id)

    def _read_path(self, course_id: str, lecture_id: str) -> Path | None:
        primary = self.path(course_id, lecture_id)
        if (primary / "index.md").exists():
            return primary
        if self.legacy_material_root is None:
            return None
        legacy = (
            self.legacy_material_root
            / "canvas"
            / "lectures"
            / _safe_id(course_id)
            / _safe_id(lecture_id)
        )
        return legacy if (legacy / "index.md").exists() else None


def _safe_id(value: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "-", value).strip("-")
    return (safe or "canvas")[:120]


def _clear_sections(canvas_dir: Path) -> None:
    sections_dir = canvas_dir / "sections"
    if not sections_dir.exists():
        return
    for path in sections_dir.glob("*.md"):
        path.unlink()
