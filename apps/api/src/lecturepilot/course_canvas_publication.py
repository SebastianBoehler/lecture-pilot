from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

from lecturepilot.canvas_learning_support import normalize_learning_support
from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.course_learning_design_models import LearningDesignReview


def legacy_safe_id(value: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "-", value).strip("-")
    return (safe or "canvas")[:120]


def clear_sections(canvas_dir: Path) -> None:
    sections_dir = canvas_dir / "sections"
    if not sections_dir.exists():
        return
    for path in sections_dir.glob("*.md"):
        path.unlink()


def prepared_document(document: CanvasDocument, canvas_dir: Path) -> CanvasDocument:
    normalized = normalize_learning_support(document).model_copy(
        update={"workspace_path": str(canvas_dir / "index.md")}
    )
    return CanvasDocument.model_validate(normalized.model_dump())


def publication_path(canvas_dir: Path) -> Path:
    return canvas_dir / "publication.json"


def read_publication(published_dir: Path) -> dict | None:
    path = publication_path(published_dir)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def publication_metadata(
    *,
    course_id: str,
    lecture_id: str,
    published_by: str,
    version: int,
    draft_dir: Path,
    published_dir: Path,
    review: LearningDesignReview,
) -> dict:
    approval = review.approval
    assert approval is not None
    return {
        "schema_version": 1,
        "course_id": course_id,
        "lecture_id": lecture_id,
        "version": version,
        "published_at": datetime.now(UTC).isoformat(),
        "published_by": published_by,
        "source_draft_path": str(draft_dir / "index.md"),
        "published_path": str(published_dir / "index.md"),
        "draft_digest": review.draft_digest,
        "source_revision": review.source_revision,
        "learning_map_revision": review.learning_map.revision,
        "learning_design_approved_by": approval.approved_by,
        "learning_design_approved_at": approval.approved_at.isoformat(),
    }
