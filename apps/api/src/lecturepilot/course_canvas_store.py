from __future__ import annotations

import json
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from pydantic import ValidationError

from lecturepilot import learning_map as learning_maps
from lecturepilot.canvas_snapshot import locked_canvas_paths, replace_canvas_snapshot
from lecturepilot.canvas_learning_support import normalize_learning_support
from lecturepilot.canvas_markdown import (
    CanvasMarkdownError,
    read_document_source,
    write_document_source,
)
from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.course_canvas_publication import (
    clear_sections,
    legacy_safe_id,
    publication_metadata,
    publication_path,
    prepared_document,
    read_publication,
)
from lecturepilot.course_canvas_context import (
    AnalyticsPublicationContext,
    PublishedCanvasSnapshot,
    read_analytics_context,
    read_current_published_snapshot,
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
            document = prepared_document(document, canvas_dir)
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
                return document
            except (CanvasMarkdownError, ValidationError, ValueError) as exc:
                raise InvalidCanvasDraftError(
                    "Stored canvas draft is invalid. Retry generation for this lecture."
                ) from exc

    def write_draft(
        self,
        document: CanvasDocument,
        *,
        expected_source_revision: str | None = None,
    ) -> CanvasDocument:
        draft_dir = self.draft_path(document.course_id, document.lecture_id)
        current_source_revision = lecture_source_revision(
            self.layout,
            course_id=document.course_id,
            lecture_id=document.lecture_id,
        )
        if (
            expected_source_revision is not None
            and current_source_revision != expected_source_revision
        ):
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

    def publish_draft(self, *, course_id: str, lecture_id: str, published_by: str) -> dict:
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
            previous = read_publication(published_dir)
            version = int(previous.get("version", 0)) + 1 if previous else 1
            metadata = publication_metadata(
                course_id=course_id,
                lecture_id=lecture_id,
                published_by=published_by,
                version=version,
                draft_dir=draft_dir,
                published_dir=published_dir,
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

    def publication(self, *, course_id: str, lecture_id: str) -> dict | None:
        published_dir = self.path(course_id, lecture_id)
        with locked_canvas_paths(published_dir):
            return read_publication(published_dir)

    def read_published_snapshot(
        self, *, course_id: str, lecture_id: str, expected_version: int
    ) -> PublishedCanvasSnapshot | None:
        return read_published_snapshot(
            self.path(course_id, lecture_id), expected_version=expected_version
        )

    def read_current_published_snapshot(
        self, *, course_id: str, lecture_id: str
    ) -> PublishedCanvasSnapshot | None:
        return read_current_published_snapshot(self.path(course_id, lecture_id))

    def read_analytics_context(
        self, *, course_id: str, lecture_id: str
    ) -> AnalyticsPublicationContext:
        return read_analytics_context(self.path(course_id, lecture_id))

    def learning_map(
        self, *, course_id: str, lecture_id: str, draft: bool = False
    ) -> learning_maps.LearningMap | None:
        canvas_dir = (
            self.draft_path(course_id, lecture_id) if draft else self.path(course_id, lecture_id)
        )
        with locked_canvas_paths(canvas_dir):
            return learning_maps.read_learning_map(canvas_dir)

    @contextmanager
    def locked_published_learning_map(
        self, *, course_id: str, lecture_id: str
    ) -> Iterator[learning_maps.LearningMap | None]:
        published_dir = self.path(course_id, lecture_id)
        with locked_canvas_paths(published_dir):
            yield learning_maps.read_learning_map(published_dir)

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
            / legacy_safe_id(course_id)
            / legacy_safe_id(lecture_id)
        )
        return legacy if (legacy / "index.md").exists() else None


def _write_validated_draft(
    document: CanvasDocument,
    staging: Path,
    source_revision: str | None,
) -> CanvasDocument:
    write_document_source(document, staging)
    normalized = normalize_learning_support(read_document_source(staging))
    learning_maps.write_learning_map(normalized, staging)
    if source_revision is not None:
        initialize_learning_design(normalized, staging, source_revision)
    return normalized


def _write_validated_canvas(
    *,
    document: CanvasDocument,
    current: Path,
    staging: Path,
) -> CanvasDocument:
    if current.exists():
        shutil.copytree(current, staging, dirs_exist_ok=True)
    clear_sections(staging)
    write_document_source(document, staging)
    normalized = normalize_learning_support(read_document_source(staging))
    learning_maps.write_learning_map(normalized, staging)
    return normalized


def _write_validated_publication(
    *,
    draft_dir: Path,
    staging: Path,
    published_dir: Path,
    metadata: dict,
    review: LearningDesignReview,
) -> dict:
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
    publication_path(staging).write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    normalize_learning_support(read_document_source(staging))
    return read_publication(staging) or {}
