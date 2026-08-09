from __future__ import annotations

import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from pydantic import ValidationError

from lecturepilot import learning_map as learning_maps
from lecturepilot.canvas_snapshot import (
    locked_canvas_access,
    locked_canvas_paths,
    replace_canvas_snapshot,
)
from lecturepilot.canvas_learning_support import normalize_learning_support
from lecturepilot.canvas_markdown import (
    CanvasMarkdownError,
    read_document_source,
    write_document_source,
)
from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.course_canvas_publication import (
    CanvasPublicationMetadata,
    publication_metadata,
    publication_path,
    prepared_document,
)
from lecturepilot.course_canvas_context import (
    AnalyticsPublicationContext,
    PublishedCanvasSnapshot,
    read_analytics_context,
    read_current_published_snapshot,
    read_published_snapshot_locked,
    read_published_snapshot,
)
from lecturepilot.course_canvas_repairs import lecture_source_revision
from lecturepilot.course_learning_design_models import LearningDesignReview
from lecturepilot.course_learning_design_store import (
    LearningDesignError,
    approved_learning_design,
    initialize_learning_design,
)
from lecturepilot.learning_map import learning_map_path
from lecturepilot.quiz_identity import validate_unique_quiz_ids
from lecturepilot.storage_layout import StorageLayout


class InvalidCanvasDraftError(RuntimeError):
    pass


class CourseCanvasStore:
    def __init__(self, layout: StorageLayout) -> None:
        self.layout = layout

    def read_draft(self, *, course_id: str, lecture_id: str) -> CanvasDocument | None:
        draft_dir = self.draft_path(course_id, lecture_id)
        with locked_canvas_paths(draft_dir):
            if not (draft_dir / "index.md").exists():
                return None
            try:
                document = normalize_learning_support(read_document_source(draft_dir))
                return document
            except (CanvasMarkdownError, ValidationError, ValueError) as exc:
                raise InvalidCanvasDraftError(
                    "Stored canvas draft is invalid. Retry generation for this lecture."
                ) from exc

    def write_draft(
        self,
        document: CanvasDocument,
        *,
        expected_source_revision: str,
    ) -> CanvasDocument:
        draft_dir = self.draft_path(document.course_id, document.lecture_id)
        current_source_revision = lecture_source_revision(
            self.layout,
            course_id=document.course_id,
            lecture_id=document.lecture_id,
        )
        if current_source_revision != expected_source_revision:
            raise InvalidCanvasDraftError(
                "Course sources changed during generation. Generate this draft again."
            )
        try:
            learning_maps.validate_learning_contract_ids(document)
            document = prepared_document(document, draft_dir)
        except (CanvasMarkdownError, ValidationError, ValueError) as exc:
            raise InvalidCanvasDraftError(
                "Generated canvas draft is invalid and was not saved."
            ) from exc
        with locked_canvas_paths(draft_dir):
            try:
                written = replace_canvas_snapshot(
                    draft_dir,
                    lambda staging: _write_validated_draft(
                        document, staging, current_source_revision
                    ),
                )
            except (CanvasMarkdownError, ValidationError, ValueError) as exc:
                raise InvalidCanvasDraftError(
                    "Generated canvas draft is invalid and was not saved."
                ) from exc
        return written.model_copy(update={"workspace_path": str(draft_dir / "index.md")})

    def publish_draft(
        self, *, course_id: str, lecture_id: str, published_by: str
    ) -> CanvasPublicationMetadata:
        draft_dir = self.draft_path(course_id, lecture_id)
        published_dir = self.path(course_id, lecture_id)
        with locked_canvas_paths(draft_dir, published_dir):
            if not (draft_dir / "index.md").exists():
                raise FileNotFoundError("No canvas draft exists for this lecture.")
            try:
                draft = read_document_source(draft_dir)
                validate_unique_quiz_ids(draft)
                learning_maps.validate_learning_contract_ids(draft)
                review = approved_learning_design(
                    self.layout,
                    draft_dir=draft_dir,
                    course_id=course_id,
                    lecture_id=lecture_id,
                )
            except LearningDesignError:
                raise
            except (CanvasMarkdownError, ValidationError, ValueError) as exc:
                raise InvalidCanvasDraftError(
                    "Stored canvas draft is invalid. Retry generation for this lecture."
                ) from exc
            previous = read_published_snapshot_locked(
                published_dir,
                course_id=course_id,
                lecture_id=lecture_id,
            )
            version = previous.version + 1 if previous else 1
            metadata = publication_metadata(
                course_id=course_id,
                lecture_id=lecture_id,
                published_by=published_by,
                version=version,
                review=review,
            )
            try:
                return replace_canvas_snapshot(
                    published_dir,
                    lambda staging: _write_validated_publication(
                        draft_dir=draft_dir,
                        staging=staging,
                        published_dir=published_dir,
                        metadata=metadata,
                        review=review,
                    ),
                )
            except (CanvasMarkdownError, ValidationError, ValueError) as exc:
                raise InvalidCanvasDraftError(
                    "Stored canvas draft is invalid. Retry generation for this lecture."
                ) from exc

    def publication(self, *, course_id: str, lecture_id: str) -> CanvasPublicationMetadata | None:
        snapshot = self.read_current_published_snapshot(
            course_id=course_id,
            lecture_id=lecture_id,
        )
        return snapshot.publication if snapshot else None

    def read_published_snapshot(
        self, *, course_id: str, lecture_id: str, expected_version: int
    ) -> PublishedCanvasSnapshot | None:
        return read_published_snapshot(
            self.path(course_id, lecture_id),
            course_id=course_id,
            lecture_id=lecture_id,
            expected_version=expected_version,
        )

    def read_current_published_snapshot(
        self, *, course_id: str, lecture_id: str
    ) -> PublishedCanvasSnapshot | None:
        return read_current_published_snapshot(
            self.path(course_id, lecture_id),
            course_id=course_id,
            lecture_id=lecture_id,
        )

    def read_analytics_context(
        self, *, course_id: str, lecture_id: str
    ) -> AnalyticsPublicationContext:
        return read_analytics_context(
            self.path(course_id, lecture_id),
            course_id=course_id,
            lecture_id=lecture_id,
        )

    def learning_map(
        self, *, course_id: str, lecture_id: str, draft: bool = False
    ) -> learning_maps.LearningMap | None:
        if not draft:
            snapshot = self.read_current_published_snapshot(
                course_id=course_id,
                lecture_id=lecture_id,
            )
            return snapshot.learning_map if snapshot else None
        canvas_dir = self.draft_path(course_id, lecture_id)
        with locked_canvas_paths(canvas_dir):
            return learning_maps.read_learning_map(canvas_dir)

    @contextmanager
    def locked_published_learning_map(
        self, *, course_id: str, lecture_id: str
    ) -> Iterator[learning_maps.LearningMap | None]:
        published_dir = self.path(course_id, lecture_id)
        with locked_canvas_access(published_dir):
            snapshot = read_published_snapshot_locked(
                published_dir,
                course_id=course_id,
                lecture_id=lecture_id,
            )
            yield snapshot.learning_map if snapshot else None

    def path(self, course_id: str, lecture_id: str) -> Path:
        return self.layout.course_canvas_dir(course_id, lecture_id)

    def draft_path(self, course_id: str, lecture_id: str) -> Path:
        return self.layout.course_canvas_draft_dir(course_id, lecture_id)


def _write_validated_draft(
    document: CanvasDocument,
    staging: Path,
    source_revision: str,
) -> CanvasDocument:
    write_document_source(document, staging)
    normalized = normalize_learning_support(read_document_source(staging))
    learning_maps.write_learning_map(normalized, staging)
    initialize_learning_design(normalized, staging, source_revision)
    return normalized


def _write_validated_publication(
    *,
    draft_dir: Path,
    staging: Path,
    published_dir: Path,
    metadata: CanvasPublicationMetadata,
    review: LearningDesignReview,
) -> CanvasPublicationMetadata:
    shutil.copytree(draft_dir, staging, dirs_exist_ok=True)
    (staging / "learning-design.json").unlink(missing_ok=True)
    document = normalize_learning_support(read_document_source(staging))
    write_document_source(
        document.model_copy(update={"workspace_path": str(published_dir / "index.md")}),
        staging,
    )
    learning_map_path(staging).write_text(
        review.learning_map.model_dump_json(indent=2), encoding="utf-8"
    )
    publication_path(staging).write_text(metadata.model_dump_json(indent=2), encoding="utf-8")
    snapshot = read_published_snapshot_locked(
        staging,
        course_id=metadata.course_id,
        lecture_id=metadata.lecture_id,
    )
    if snapshot is None:
        raise InvalidCanvasDraftError("Published canvas snapshot is incomplete.")
    return snapshot.publication
