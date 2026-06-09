from __future__ import annotations

import re
from pathlib import Path

from lecturepilot.canvas_markdown import read_document_source, write_document_source
from lecturepilot.canvas_models import CanvasDocument


class CourseCanvasStore:
    def __init__(self, material_root: Path) -> None:
        self.material_root = material_root

    def read(
        self,
        *,
        course_id: str,
        lecture_id: str,
        workspace_path: str,
    ) -> CanvasDocument | None:
        canvas_dir = self.path(course_id, lecture_id)
        if not (canvas_dir / "index.md").exists():
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
        return self.material_root / "canvas" / "lectures" / _safe_id(course_id) / _safe_id(lecture_id)


def _safe_id(value: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "-", value).strip("-")
    return (safe or "canvas")[:120]


def _clear_sections(canvas_dir: Path) -> None:
    sections_dir = canvas_dir / "sections"
    if not sections_dir.exists():
        return
    for path in sections_dir.glob("*.md"):
        path.unlink()
