"""Derive every lecture's source, goal and draft state from stored files.

Cheap by construction: no model calls, no source parsing and no course lock. It reads the
schedule, source index, routing, practice designs, goal-proposal markers, draft bindings,
publication metadata (validity comes from the workspace's validity cache) and only the
newest generation record per lecture.
"""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import re

from fastapi import FastAPI, HTTPException
from pydantic import ValidationError

from lecturepilot.authoring.course_canvas_generation_jobs import CanvasGenerationJob
from lecturepilot.authoring.course_canvas_generation_service import (
    CANVAS_GENERATION_LEASE_SECONDS,
)
from lecturepilot.authoring.course_canvas_publication import (
    CanvasPublicationMetadata,
    InvalidCanvasPublicationMetadataError,
    read_publication,
)
from lecturepilot.core.models import Lecture
from lecturepilot.core.storage_layout import StorageLayout, safe_id
from lecturepilot.courses.course_publication_visibility import published_canvas_is_ready
from lecturepilot.courses.course_schedule_store import read_course_workspace
from lecturepilot.courses.course_update_analysis import lecture_number
from lecturepilot.courses.lecture_state_models import (
    CourseLectureStates,
    LectureState,
    next_action,
)
from lecturepilot.learning_design.course_learning_intent import has_approved_intent
from lecturepilot.learning_design.course_practice_design_binding import (
    PracticeDesignBindingError,
    read_practice_design_binding,
)
from lecturepilot.learning_design.course_practice_design_models import PracticeDesign
from lecturepilot.learning_design.course_practice_design_store import (
    PracticeDesignStore,
    PracticeDesignUnavailable,
)
from lecturepilot.learning_design.learning_goal_proposal_jobs import read_goal_proposal
from lecturepilot.sources.course_source_routing import read_source_routing, source_revision
from lecturepilot.sources.lecture_source_revision import CourseSourceInputs
from lecturepilot.sources.source_index_models import CourseSourceIndex

_JOB_FILE = re.compile(r"^[a-f0-9]{64}\.json$")
_INTERRUPTED = "Generation was interrupted; retry resumes the saved work."


def course_lecture_states(app: FastAPI, course_id: str) -> CourseLectureStates:
    layout = app.state.canvas_workspace.layout
    workspace = read_course_workspace(layout.course_root(course_id), course_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Course workspace not found.")
    routing = "confirmed" if _routing_current(layout, course_id, workspace.lectures) else None
    inputs = CourseSourceInputs.load(layout, course_id)
    return CourseLectureStates(
        course_id=course_id,
        routing=routing or "needs_review",
        lectures=[
            _lecture_state(app, inputs, lecture, index, routing or "needs_review")
            for index, lecture in enumerate(workspace.lectures, start=1)
        ],
    )


def _lecture_state(app, inputs, lecture: Lecture, position: int, routing) -> LectureState:
    layout, course_id = inputs.layout, inputs.course_id
    current = inputs.revision(lecture.id)
    design = _design(layout, course_id, lecture.id)
    approved = design is not None and has_approved_intent(design)
    published = published_canvas_is_ready(
        app, course_id=course_id, lecture_id=lecture.id, invalid_as_unavailable=True
    )
    publication = _publication(layout, course_id, lecture.id) if published else None
    proposal = read_goal_proposal(layout, course_id, lecture.id)
    if approved and design.source_revision == current:
        goals = "approved"
    elif proposal is not None and proposal.proposing():
        goals = "proposing"
    elif approved:
        goals = "stale"
    elif design is not None and design.source_revision == current:
        goals = "needs_review"
    else:
        goals = "missing"
    bindings = [(publication.published_at, publication.source_revision)] if publication else []
    if approved:
        intent_approval = design.learning_intent.approval
        bindings.append((intent_approval.approved_at, design.source_revision))
    if not bindings:
        sources = "new"
    else:
        sources = "current" if max(bindings)[1] == current else "changed"
    draft, draft_error = _draft_state(
        layout, course_id, lecture.id, design if goals == "approved" else None, publication
    )
    return LectureState(
        lecture_id=lecture.id,
        number=lecture_number(lecture.id, position),
        title=lecture.title,
        date=lecture.date,
        published=published,
        published_at=publication.published_at if publication else None,
        sources=sources,
        goals=goals,
        draft=draft,
        draft_error=draft_error,
        next_action=next_action(routing, goals, draft),
    )


def _draft_state(
    layout: StorageLayout,
    course_id: str,
    lecture_id: str,
    design: PracticeDesign | None,
    publication: CanvasPublicationMetadata | None,
) -> tuple[str, str | None]:
    """`design` is the practice design only when its goals are approved for current sources."""
    job = latest_generation(layout, course_id, lecture_id)
    age = (datetime.now(UTC) - job.updated_at).total_seconds() if job else 0
    if job is not None and job.status == "running" and age <= CANVAS_GENERATION_LEASE_SECONDS:
        return "generating", None
    if design is None:
        return "none", None
    published = publication is not None and publication_current(publication, design)
    failure = _failure(job, design.learning_intent.approval.approved_at)
    draft_digest = current_draft_digest(layout, course_id, lecture_id, design)
    if draft_digest is not None and (not published or draft_digest != publication.draft_digest):
        # A later failed attempt (e.g. a change request) keeps the draft but reports why.
        drafted_at = _modified_at(
            layout.course_canvas_draft_dir(course_id, lecture_id) / "index.md"
        )
        return "ready", failure if failure and job.updated_at > drafted_at else None
    if published:
        return (
            "published",
            failure if failure and job.updated_at > publication.published_at else None,
        )
    if failure:
        return "failed", failure
    return "none", None


def _failure(job: CanvasGenerationJob | None, approved_at: datetime) -> str | None:
    """The readable detail of the newest generation when it failed after the goal approval."""
    if job is None or job.status == "completed" or job.updated_at < approved_at:
        return None
    if job.status == "running" or job.error_code == "interrupted":
        return readable_draft_error(job.error_detail) or _INTERRUPTED
    return readable_draft_error(job.error_detail) or "Draft generation failed. Retry the draft."


def _modified_at(path: Path) -> datetime:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, UTC)
    except OSError:
        return datetime.max.replace(tzinfo=UTC)


_INTERNAL_PATH_PREFIX = re.compile(r"^/[\w./-]+\.(?:md|json|yaml):\s*")


def readable_draft_error(detail: str | None) -> str | None:
    """Drop internal draft file paths from a stored failure detail shown to professors."""
    if not detail:
        return None
    return _INTERNAL_PATH_PREFIX.sub("", detail.strip()) or None


def publication_current(publication: CanvasPublicationMetadata, design: PracticeDesign) -> bool:
    if publication.source_revision != design.source_revision:
        return False
    if publication.learning_intent_revision is not None:
        return publication.learning_intent_revision == design.learning_intent.revision
    return publication.practice_design_revision == design.revision


def current_draft_digest(layout, course_id, lecture_id, design) -> str | None:
    draft_dir = layout.course_canvas_draft_dir(course_id, lecture_id)
    if not (draft_dir / "index.md").exists():
        return None
    try:
        binding = read_practice_design_binding(draft_dir)
        review = json.loads((draft_dir / "learning-design.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, PracticeDesignBindingError):
        return None
    if (
        binding.source_revision != design.source_revision
        or binding.practice_design_revision != design.revision
        or review.get("source_revision") != design.source_revision
    ):
        return None
    digest = review.get("draft_digest")
    return digest if isinstance(digest, str) else None


def latest_generation(layout, course_id: str, lecture_id: str) -> CanvasGenerationJob | None:
    directory = layout.course_root(course_id) / "builder" / "generations" / safe_id(lecture_id)
    if not directory.is_dir():
        return None
    records = [path for path in directory.iterdir() if _JOB_FILE.match(path.name)]
    # Records are rewritten on every status change and heartbeat: the newest file wins.
    for path in sorted(records, key=_mtime, reverse=True)[:1]:
        try:
            return CanvasGenerationJob.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValidationError):
            return None
    return None


def _mtime(path: Path) -> int:
    try:
        return path.stat().st_mtime_ns
    except OSError:
        return 0


def _design(layout, course_id: str, lecture_id: str) -> PracticeDesign | None:
    try:
        return PracticeDesignStore(layout).read(course_id=course_id, lecture_id=lecture_id)
    except PracticeDesignUnavailable:
        return None


def _publication(layout, course_id: str, lecture_id: str) -> CanvasPublicationMetadata | None:
    try:
        return read_publication(layout.course_canvas_dir(course_id, lecture_id))
    except InvalidCanvasPublicationMetadataError:
        return None


def _routing_current(layout: StorageLayout, course_id: str, lectures: list[Lecture]) -> bool:
    routing = read_source_routing(layout.course_source_routing_path(course_id), course_id)
    path = layout.course_source_index_path(course_id)
    if routing is None or not routing.confirmed or not path.exists():
        return False
    try:
        index = CourseSourceIndex.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError):
        return False
    return routing.source_revision == source_revision(index, lectures)
