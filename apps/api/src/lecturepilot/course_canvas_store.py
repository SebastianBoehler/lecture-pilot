from __future__ import annotations

import json
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path

from lecturepilot.canvas_learning_support import normalize_learning_support
from lecturepilot.canvas_markdown import read_document_source, write_document_source
from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.learning_map import write_learning_map
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
        return normalize_learning_support(read_document_source(canvas_dir)).model_copy(
            update={"workspace_path": workspace_path}
        )

    def write(self, document: CanvasDocument) -> CanvasDocument:
        canvas_dir = self.path(document.course_id, document.lecture_id)
        _clear_sections(canvas_dir)
        write_document_source(
            normalize_learning_support(document).model_copy(
                update={"workspace_path": str(canvas_dir / "index.md")}
            ),
            canvas_dir,
        )
        document = normalize_learning_support(read_document_source(canvas_dir))
        write_learning_map(document, canvas_dir)
        return document

    def read_draft(self, *, course_id: str, lecture_id: str) -> CanvasDocument | None:
        draft_dir = self.draft_path(course_id, lecture_id)
        if not (draft_dir / "index.md").exists():
            return None
        document = normalize_learning_support(read_document_source(draft_dir))
        write_learning_map(document, draft_dir)
        return document

    def write_draft(self, document: CanvasDocument) -> CanvasDocument:
        draft_dir = self.draft_path(document.course_id, document.lecture_id)
        _replace_canvas_dir(draft_dir)
        write_document_source(
            normalize_learning_support(document).model_copy(
                update={"workspace_path": str(draft_dir / "index.md")}
            ),
            draft_dir,
        )
        return normalize_learning_support(read_document_source(draft_dir))

    def publish_draft(self, *, course_id: str, lecture_id: str, published_by: str) -> dict:
        draft_dir = self.draft_path(course_id, lecture_id)
        if not (draft_dir / "index.md").exists():
            raise FileNotFoundError("No canvas draft exists for this lecture.")
        published_dir = self.path(course_id, lecture_id)
        previous = self.publication(course_id=course_id, lecture_id=lecture_id)
        version = int(previous.get("version", 0)) + 1 if previous else 1
        _replace_canvas_dir(published_dir)
        shutil.copytree(draft_dir, published_dir, dirs_exist_ok=True)
        document = normalize_learning_support(read_document_source(published_dir))
        write_document_source(
            document.model_copy(update={"workspace_path": str(published_dir / "index.md")}),
            published_dir,
        )
        write_learning_map(document, published_dir)
        metadata = {
            "schema_version": 1,
            "course_id": course_id,
            "lecture_id": lecture_id,
            "version": version,
            "published_at": datetime.now(UTC).isoformat(),
            "published_by": published_by,
            "source_draft_path": str(draft_dir / "index.md"),
            "published_path": str(published_dir / "index.md"),
        }
        _publication_path(published_dir).write_text(
            json.dumps(metadata, indent=2), encoding="utf-8"
        )
        return metadata

    def publication(self, *, course_id: str, lecture_id: str) -> dict | None:
        path = _publication_path(self.path(course_id, lecture_id))
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def path(self, course_id: str, lecture_id: str) -> Path:
        return self.layout.course_canvas_dir(course_id, lecture_id)

    def draft_path(self, course_id: str, lecture_id: str) -> Path:
        return self.layout.course_canvas_draft_dir(course_id, lecture_id)

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


def _replace_canvas_dir(canvas_dir: Path) -> None:
    if canvas_dir.exists():
        shutil.rmtree(canvas_dir)
    canvas_dir.mkdir(parents=True, exist_ok=True)


def _publication_path(canvas_dir: Path) -> Path:
    return canvas_dir / "publication.json"
