from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, PositiveInt, ValidationError

from lecturepilot.canvas_learning_support import normalize_learning_support
from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.course_learning_design_models import LearningDesignReview


class CanvasPublicationMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal[1]
    course_id: str = Field(min_length=1, max_length=120)
    lecture_id: str = Field(min_length=1, max_length=120)
    version: PositiveInt
    source_revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    draft_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    learning_map_revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    published_at: AwareDatetime
    published_by: str = Field(min_length=1, max_length=160)


class InvalidCanvasPublicationMetadataError(ValueError):
    pass


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


def read_publication(published_dir: Path) -> CanvasPublicationMetadata | None:
    path = publication_path(published_dir)
    if not path.exists():
        return None
    try:
        return CanvasPublicationMetadata.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as exc:
        raise InvalidCanvasPublicationMetadataError(
            "Published canvas metadata is invalid. Publish the canvas again."
        ) from exc


def publication_metadata(
    *,
    course_id: str,
    lecture_id: str,
    published_by: str,
    version: int,
    review: LearningDesignReview,
) -> CanvasPublicationMetadata:
    approval = review.approval
    assert approval is not None
    return CanvasPublicationMetadata(
        schema_version=1,
        course_id=course_id,
        lecture_id=lecture_id,
        version=version,
        published_at=datetime.now(UTC),
        published_by=published_by,
        draft_digest=review.draft_digest,
        source_revision=review.source_revision,
        learning_map_revision=review.learning_map.revision,
    )
