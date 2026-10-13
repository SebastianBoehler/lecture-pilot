"""The document a professor change request starts from.

Blocking but cheap: hashes source files and reads stored drafts, never parses sources or calls a
model. The base is the ready draft bound to the current approved goals and sources, else the
publication bound to exactly that approved implementation. Anything else needs a new draft.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from lecturepilot.authoring.course_canvas_generation_service import (
    CANVAS_GENERATION_LEASE_SECONDS,
)
from lecturepilot.authoring.course_canvas_publication import (
    InvalidCanvasPublicationMetadataError,
    read_publication,
)
from lecturepilot.authoring.course_canvas_repairs import lecture_source_revision
from lecturepilot.canvas.canvas_models import CanvasDocument
from lecturepilot.canvas.course_canvas_store import CourseCanvasStore, InvalidCanvasDraftError
from lecturepilot.core.storage_layout import StorageLayout
from lecturepilot.courses.lecture_states import (
    current_draft_digest,
    latest_generation,
    publication_current,
)
from lecturepilot.learning_design.course_learning_intent import has_approved_intent
from lecturepilot.learning_design.course_practice_design_models import PracticeDesign
from lecturepilot.learning_design.course_practice_design_store import (
    PracticeDesignStore,
    PracticeDesignUnavailable,
)


class ChangeRequestUnavailable(RuntimeError):
    """The lecture has nothing a change request may start from (HTTP 409)."""


@dataclass(frozen=True)
class ChangeBase:
    kind: Literal["draft", "published"]
    document: CanvasDocument
    design: PracticeDesign


def change_request_base(
    layout: StorageLayout, *, course_id: str, lecture_id: str, allow_running: bool = False
) -> ChangeBase:
    try:
        design = PracticeDesignStore(layout).read(course_id=course_id, lecture_id=lecture_id)
    except PracticeDesignUnavailable:
        design = None
    revision = lecture_source_revision(layout, course_id=course_id, lecture_id=lecture_id)
    if design is None or not has_approved_intent(design) or design.source_revision != revision:
        raise ChangeRequestUnavailable(
            "Approve this lecture's learning goals for its current sources before requesting "
            "a change."
        )
    job = latest_generation(layout, course_id, lecture_id)
    if not allow_running and job is not None and job.status == "running":
        age = (datetime.now(UTC) - job.updated_at).total_seconds()
        if age <= CANVAS_GENERATION_LEASE_SECONDS:
            raise ChangeRequestUnavailable(
                "A draft is already being generated for this lecture. Wait until it finishes."
            )
    store = CourseCanvasStore(layout)
    try:
        publication = read_publication(layout.course_canvas_dir(course_id, lecture_id))
    except InvalidCanvasPublicationMetadataError:
        publication = None
    published = (
        publication is not None
        and publication_current(publication, design)
        and publication.practice_design_revision == design.revision
    )
    digest = current_draft_digest(layout, course_id, lecture_id, design)
    # A ready draft differs from the publication; an equal one is the publication itself.
    if digest is not None and not (published and digest == publication.draft_digest):
        try:
            document = store.read_draft(course_id=course_id, lecture_id=lecture_id)
        except InvalidCanvasDraftError as exc:
            raise ChangeRequestUnavailable(str(exc)) from exc
        if document is not None:
            return ChangeBase("draft", document, design)
    if published:
        snapshot = store.read_current_published_snapshot(course_id=course_id, lecture_id=lecture_id)
        if snapshot is not None:
            return ChangeBase("published", snapshot.document, design)
    raise ChangeRequestUnavailable(
        "This lecture has no draft or publication for its current learning goals. "
        "Generate a draft first."
    )
