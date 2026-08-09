from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from lecturepilot import learning_map as learning_maps
from lecturepilot.canvas_learning_support import normalize_learning_support
from lecturepilot.canvas_markdown import CanvasMarkdownError, read_document_source
from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.canvas_snapshot import locked_canvas_access
from lecturepilot.course_canvas_publication import (
    CanvasPublicationMetadata,
    InvalidCanvasPublicationMetadataError,
    publication_path,
    read_publication,
)
from lecturepilot.course_learning_design_store import canvas_digest


@dataclass(frozen=True)
class PublishedCanvasSnapshot:
    document: CanvasDocument
    publication: CanvasPublicationMetadata
    learning_map: learning_maps.LearningMap

    @property
    def version(self) -> int:
        return self.publication.version

    @property
    def learning_map_revision(self) -> str:
        return self.learning_map.revision


@dataclass(frozen=True)
class AnalyticsPublicationContext:
    learning_map: learning_maps.LearningMap
    publication_version: int
    learning_map_revision: str


class InvalidPublishedCanvasContextError(RuntimeError):
    pass


class StalePublishedCanvasVersionError(RuntimeError):
    pass


def read_published_snapshot(
    published_dir: Path,
    *,
    course_id: str,
    lecture_id: str,
    expected_version: int,
) -> PublishedCanvasSnapshot | None:
    with locked_canvas_access(published_dir):
        snapshot = read_published_snapshot_locked(
            published_dir,
            course_id=course_id,
            lecture_id=lecture_id,
        )
        if snapshot is not None and snapshot.version != expected_version:
            raise StalePublishedCanvasVersionError
        return snapshot


def read_current_published_snapshot(
    published_dir: Path, *, course_id: str, lecture_id: str
) -> PublishedCanvasSnapshot | None:
    with locked_canvas_access(published_dir):
        return read_published_snapshot_locked(
            published_dir,
            course_id=course_id,
            lecture_id=lecture_id,
        )


def read_analytics_context(
    published_dir: Path, *, course_id: str, lecture_id: str
) -> AnalyticsPublicationContext:
    snapshot = read_current_published_snapshot(
        published_dir,
        course_id=course_id,
        lecture_id=lecture_id,
    )
    if snapshot is None:
        raise InvalidPublishedCanvasContextError("Publish the canvas before using it.")
    return AnalyticsPublicationContext(
        learning_map=snapshot.learning_map,
        publication_version=snapshot.version,
        learning_map_revision=snapshot.learning_map_revision,
    )


def read_published_snapshot_locked(
    published_dir: Path, *, course_id: str, lecture_id: str
) -> PublishedCanvasSnapshot | None:
    index_exists = (published_dir / "index.md").exists()
    metadata_exists = publication_path(published_dir).exists()
    map_exists = learning_maps.learning_map_path(published_dir).exists()
    if not any((index_exists, metadata_exists, map_exists)):
        return None
    if not all((index_exists, metadata_exists, map_exists)):
        raise InvalidPublishedCanvasContextError(
            "Published canvas snapshot is incomplete. Publish the canvas again."
        )
    try:
        publication = read_publication(published_dir)
        learning_map = learning_maps.read_strict_published_learning_map(published_dir)
        document = normalize_learning_support(read_document_source(published_dir))
    except (
        CanvasMarkdownError,
        InvalidCanvasPublicationMetadataError,
        OSError,
        TypeError,
        ValidationError,
        ValueError,
    ) as exc:
        raise InvalidPublishedCanvasContextError(
            "Published canvas snapshot is invalid. Publish the canvas again."
        ) from exc
    if publication is None or learning_map is None:
        raise InvalidPublishedCanvasContextError(
            "Published canvas snapshot is incomplete. Publish the canvas again."
        )
    if (
        publication.course_id != course_id
        or publication.lecture_id != lecture_id
        or document.course_id != course_id
        or document.lecture_id != lecture_id
        or learning_map.course_id != course_id
        or learning_map.lecture_id != lecture_id
    ):
        raise InvalidPublishedCanvasContextError(
            "Published canvas snapshot identity does not match the requested lecture."
        )
    if publication.learning_map_revision != learning_map.revision:
        raise InvalidPublishedCanvasContextError(
            "Published canvas metadata does not match its learning map. Publish it again."
        )
    if publication.draft_digest != canvas_digest(document):
        raise InvalidPublishedCanvasContextError(
            "Published canvas metadata does not match its document. Publish it again."
        )
    return PublishedCanvasSnapshot(
        document=document.model_copy(update={"workspace_path": str(published_dir / "index.md")}),
        publication=publication,
        learning_map=learning_map,
    )
