"""Propose a lecture's learning goals once per source revision (route and background job)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi.concurrency import run_in_threadpool

from lecturepilot.courses.course_update_recovery import locked_course_state
from lecturepilot.learning_design.course_learning_intent import has_approved_intent
from lecturepilot.learning_design.course_learning_intent_proposal import propose_learning_intent
from lecturepilot.learning_design.course_learning_intent_store import LearningIntentStore
from lecturepilot.learning_design.course_practice_design_models import PracticeDesign
from lecturepilot.learning_design.course_practice_design_store import PracticeDesignStale
from lecturepilot.learning_design.learning_goal_support import (
    goal_findings_path,
    save_goal_findings,
)
from lecturepilot.llm.model_usage import model_usage_scope


async def propose_lecture_goals(
    app: Any,
    *,
    course_id: str,
    lecture_id: str,
    actor_user_id: str,
    refresh: bool,
    source_document: Callable,
    source_context: Callable,
    source_revision: Callable,
) -> PracticeDesign | None:
    """Return the current goals, proposing them when none exist for the current sources.

    `refresh` replaces unapproved goals. Raises PracticeDesignStale, provider errors or
    ValueError; the source callables may raise their own HTTP errors.
    """
    layout = app.state.canvas_workspace.layout
    store = LearningIntentStore(layout)

    def current_sources():
        with locked_course_state(layout.course_root(course_id)):
            revision = source_revision(app, course_id, lecture_id)
            snapshot = store.snapshot(course_id=course_id, lecture_id=lecture_id)
        existing = snapshot.design
        current = existing is not None and existing.source_revision == revision
        if current and refresh and has_approved_intent(existing):
            raise PracticeDesignStale(
                "These learning goals are approved. Edit them to propose new goals."
            )
        if current and not refresh:
            return snapshot, None
        # Parsing (conversion, LaTeX, OCR) never holds the course lock.
        return snapshot, source_context(app, source_document, course_id, lecture_id)

    snapshot, loaded = await run_in_threadpool(current_sources)
    existing = snapshot.design
    if loaded is None:
        return existing
    source, revision, paths = loaded

    def save(proposal):
        with locked_course_state(layout.course_root(course_id)):
            # Same revision means the same confirmed files, so the parsed source still holds.
            if source_revision(app, course_id, lecture_id) != revision:
                raise PracticeDesignStale("Course sources changed while goals were proposed.")
            return store.save_goals(
                expected=existing,
                expected_invalid_digest=snapshot.invalid_digest,
                course_id=course_id,
                lecture_id=lecture_id,
                source_revision=revision,
                proposal=proposal,
                source=source,
                allowed_source_paths=paths,
            )

    with model_usage_scope(
        actor_user_id=actor_user_id,
        course_id=course_id,
        workload="course_learning_intent",
    ):
        proposal, findings = await propose_learning_intent(
            app.state.practice_design_planner,
            source=source,
            source_revision=revision,
            allowed_source_paths=paths,
        )
    saved = await run_in_threadpool(save, proposal)
    save_goal_findings(goal_findings_path(layout, course_id, lecture_id), proposal.goals, findings)
    return saved
