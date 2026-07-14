from __future__ import annotations

import json
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from lecturepilot.canvas_snapshot import locked_canvas_paths, replace_canvas_snapshot
from lecturepilot.canvas_learning_support import normalize_learning_support
from lecturepilot.canvas_markdown import (
    CanvasMarkdownError,
    read_document_source,
    write_document_source,
)
from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.learning_map import write_learning_map
from lecturepilot.storage_layout import StorageLayout


class InvalidCanvasDraftError(RuntimeError):
    """Raised when a generated or stored draft violates the canvas contract."""


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
        canvas_dir = self.path(course_id, lecture_id)
        with locked_canvas_paths(canvas_dir):
            if (canvas_dir / "index.md").exists():
                return normalize_learning_support(read_document_source(canvas_dir)).model_copy(
                    update={"workspace_path": workspace_path}
                )
        legacy = self._legacy_read_path(course_id, lecture_id)
        if legacy is None:
            return None
        return normalize_learning_support(read_document_source(legacy)).model_copy(
            update={"workspace_path": workspace_path}
        )

    def write(self, document: CanvasDocument) -> CanvasDocument:
        canvas_dir = self.path(document.course_id, document.lecture_id)
        with locked_canvas_paths(canvas_dir):
            document = _prepared_document(document, canvas_dir)
            written = replace_canvas_snapshot(
                canvas_dir,
                lambda staging: _write_validated_canvas(
                    document=document,
                    current=canvas_dir,
                    staging=staging,
                ),
            )
        return written.model_copy(update={"workspace_path": str(canvas_dir / "index.md")})

    def read_draft(self, *, course_id: str, lecture_id: str) -> CanvasDocument | None:
        draft_dir = self.draft_path(course_id, lecture_id)
        with locked_canvas_paths(draft_dir):
            if not (draft_dir / "index.md").exists():
                return None
            try:
                document = normalize_learning_support(read_document_source(draft_dir))
                write_learning_map(document, draft_dir)
                return document
            except (CanvasMarkdownError, ValidationError, ValueError) as exc:
                raise InvalidCanvasDraftError(
                    "Stored canvas draft is invalid. Retry generation for this lecture."
                ) from exc

    def write_draft(self, document: CanvasDocument) -> CanvasDocument:
        draft_dir = self.draft_path(document.course_id, document.lecture_id)
        try:
            document = _prepared_document(document, draft_dir)
        except (CanvasMarkdownError, ValidationError, ValueError) as exc:
            raise InvalidCanvasDraftError(
                "Generated canvas draft is invalid and was not saved."
            ) from exc
        with locked_canvas_paths(draft_dir):
            try:
                written = replace_canvas_snapshot(
                    draft_dir,
                    lambda staging: _write_validated_draft(document, staging),
                )
            except (CanvasMarkdownError, ValidationError, ValueError) as exc:
                raise InvalidCanvasDraftError(
                    "Generated canvas draft is invalid and was not saved."
                ) from exc
        return written.model_copy(update={"workspace_path": str(draft_dir / "index.md")})

    def publish_draft(self, *, course_id: str, lecture_id: str, published_by: str) -> dict:
        draft_dir = self.draft_path(course_id, lecture_id)
        published_dir = self.path(course_id, lecture_id)
        with locked_canvas_paths(draft_dir, published_dir):
            if not (draft_dir / "index.md").exists():
                raise FileNotFoundError("No canvas draft exists for this lecture.")
            try:
                read_document_source(draft_dir)
            except (CanvasMarkdownError, ValidationError, ValueError) as exc:
                raise InvalidCanvasDraftError(
                    "Stored canvas draft is invalid. Retry generation for this lecture."
                ) from exc
            previous = _read_publication(published_dir)
            version = int(previous.get("version", 0)) + 1 if previous else 1
            metadata = _publication_metadata(
                course_id=course_id,
                lecture_id=lecture_id,
                published_by=published_by,
                version=version,
                draft_dir=draft_dir,
                published_dir=published_dir,
            )
            return replace_canvas_snapshot(
                published_dir,
                lambda staging: _write_validated_publication(
                    draft_dir=draft_dir,
                    staging=staging,
                    published_dir=published_dir,
                    metadata=metadata,
                ),
            )

    def publication(self, *, course_id: str, lecture_id: str) -> dict | None:
        published_dir = self.path(course_id, lecture_id)
        with locked_canvas_paths(published_dir):
            return _read_publication(published_dir)

    def path(self, course_id: str, lecture_id: str) -> Path:
        return self.layout.course_canvas_dir(course_id, lecture_id)

    def draft_path(self, course_id: str, lecture_id: str) -> Path:
        return self.layout.course_canvas_draft_dir(course_id, lecture_id)

    def _legacy_read_path(self, course_id: str, lecture_id: str) -> Path | None:
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


def _prepared_document(document: CanvasDocument, canvas_dir: Path) -> CanvasDocument:
    normalized = normalize_learning_support(document).model_copy(
        update={"workspace_path": str(canvas_dir / "index.md")}
    )
    return CanvasDocument.model_validate(normalized.model_dump())


def _clear_sections(canvas_dir: Path) -> None:
    sections_dir = canvas_dir / "sections"
    if not sections_dir.exists():
        return
    for path in sections_dir.glob("*.md"):
        path.unlink()


def _publication_path(canvas_dir: Path) -> Path:
    return canvas_dir / "publication.json"


def _write_validated_draft(document: CanvasDocument, staging: Path) -> CanvasDocument:
    write_document_source(document, staging)
    return normalize_learning_support(read_document_source(staging))


def _write_validated_canvas(
    *,
    document: CanvasDocument,
    current: Path,
    staging: Path,
) -> CanvasDocument:
    if current.exists():
        shutil.copytree(current, staging, dirs_exist_ok=True)
    _clear_sections(staging)
    write_document_source(document, staging)
    normalized = normalize_learning_support(read_document_source(staging))
    write_learning_map(normalized, staging)
    return normalized


def _write_validated_publication(
    *,
    draft_dir: Path,
    staging: Path,
    published_dir: Path,
    metadata: dict,
) -> dict:
    shutil.copytree(draft_dir, staging, dirs_exist_ok=True)
    document = normalize_learning_support(read_document_source(staging))
    write_document_source(
        document.model_copy(update={"workspace_path": str(published_dir / "index.md")}),
        staging,
    )
    write_learning_map(document, staging)
    _publication_path(staging).write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    normalize_learning_support(read_document_source(staging))
    return json.loads(_publication_path(staging).read_text(encoding="utf-8"))


def _read_publication(published_dir: Path) -> dict | None:
    path = _publication_path(published_dir)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _publication_metadata(
    *,
    course_id: str,
    lecture_id: str,
    published_by: str,
    version: int,
    draft_dir: Path,
    published_dir: Path,
) -> dict:
    return {
        "schema_version": 1,
        "course_id": course_id,
        "lecture_id": lecture_id,
        "version": version,
        "published_at": datetime.now(UTC).isoformat(),
        "published_by": published_by,
        "source_draft_path": str(draft_dir / "index.md"),
        "published_path": str(published_dir / "index.md"),
    }
