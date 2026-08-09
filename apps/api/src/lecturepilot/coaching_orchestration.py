from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from fastapi import FastAPI

from lecturepilot.agent_state_access import learner_state_store
from lecturepilot.coaching_assistance import emitted_assistance_level
from lecturepilot.coaching_episode import parse_time
from lecturepilot.coaching_progress import CoachingProgressStore, CoachingTurnEvent
from lecturepilot.coaching_state_models import CoachingProgress
from lecturepilot.guided_tutor import LOCAL_PREVIEW_USER_ID
from lecturepilot.learning_gate_selector import select_active_gate
from lecturepilot.learning_gates import gate_spec_for_lecture
from lecturepilot.learning_map import LearningMap, LearningMapGate
from lecturepilot.models import (
    AgentCoachingContext,
    AgentTurnInput,
    AgentTurnResult,
    QualityGateStatus,
)
from lecturepilot.observability import Observability
from lecturepilot.scaffold_policy import scaffold_policy_for_tutor_turn


def prepare_coaching_turn(
    app: FastAPI,
    turn: AgentTurnInput,
    activity: Callable[[str], None],
    observability: Observability,
) -> AgentTurnInput:
    activity("load coaching progress")
    store = CoachingProgressStore(app.state.canvas_workspace.layout)
    progress = store.read(
        user_id=turn.user_id,
        course_id=turn.course_id,
        lecture_id=turn.lecture_id,
    )
    if turn.user_id == LOCAL_PREVIEW_USER_ID:
        spec = gate_spec_for_lecture(turn.lecture_id)
        with observability.tool_span("read_coaching_progress", gate_id=spec.gate_id):
            context = store.context(
                user_id=turn.user_id,
                course_id=turn.course_id,
                lecture_id=turn.lecture_id,
                gate_id=spec.gate_id,
                gate_title=spec.title,
            )
        active_gate = None
    else:
        learning_map = app.state.canvas_workspace.course_canvas_store.learning_map(
            course_id=turn.course_id, lecture_id=turn.lecture_id
        )
        decisions = learner_state_store(app).latest_gate_decisions(
            user_id=turn.user_id,
            course_id=turn.course_id,
            lecture_id=turn.lecture_id,
        )
        active_gate = select_due_review_gate(learning_map, progress) or (
            select_active_gate(
                learning_map,
                requested_gate_id=turn.requested_gate_id,
                focused_section_id=turn.canvas_state.focused_section_id,
                latest_decisions=decisions,
            )
            if learning_map is not None
            else None
        )
        if active_gate is None:
            context = AgentCoachingContext(attendance_prior_used=progress.attendance_prior_used)
        else:
            with observability.tool_span("read_coaching_progress", gate_id=active_gate.id):
                context = store.context(
                    user_id=turn.user_id,
                    course_id=turn.course_id,
                    lecture_id=turn.lecture_id,
                    gate_id=active_gate.id,
                    gate_title=active_gate.title,
                    gate_revision=active_gate.revision or None,
                )
            context = context.model_copy(
                update={
                    "active_gate_id": active_gate.id,
                    "active_gate_revision": active_gate.revision or None,
                    "active_gate_review_after_days": active_gate.review_after_days,
                }
            )
    policy = (
        turn.readiness_task.scaffold_policy
        if turn.readiness_task is not None
        else scaffold_policy_for_tutor_turn(
            attendance=turn.attendance.value,
            delayed_transfer_due=context.delayed_transfer_due,
            last_gate_status=context.last_gate_status,
            needs_evidence_count=context.needs_evidence_count,
            prior_assistance=(context.prior_assistance or context.attendance_prior_used),
        )
    )
    return turn.model_copy(
        update={
            "active_gate": active_gate,
            "coaching_context": context,
            "scaffold_policy": policy,
            "recent_messages": progress.messages,
        },
        deep=True,
    )


def select_due_review_gate(
    learning_map: LearningMap | None,
    progress: CoachingProgress,
    *,
    now: datetime | None = None,
) -> LearningMapGate | None:
    if learning_map is None:
        return None
    current_time = now or datetime.now(UTC)
    for gate in learning_map.gates:
        review = progress.delayed_reviews.get(gate.id)
        if (
            review is None
            or review.completed_at is not None
            or review.attempted_at is not None
            or review.gate_revision != gate.revision
        ):
            continue
        try:
            if parse_time(review.due_at) <= current_time:
                return gate
        except ValueError:
            continue
    return None


def persist_coaching_turn(
    app: FastAPI,
    turn: AgentTurnInput,
    result: AgentTurnResult,
    activity: Callable[[str], None],
    observability: Observability,
) -> CoachingTurnEvent | None:
    store = CoachingProgressStore(app.state.canvas_workspace.layout)
    if result.quality_gate is None or turn.scaffold_policy is None:
        store.record_exchange(
            user_id=turn.user_id,
            course_id=turn.course_id,
            lecture_id=turn.lecture_id,
            user_message=turn.message,
            assistant_message=result.message,
            session_goal=result.session_goal,
        )
        return None
    activity("save coaching progress")
    with observability.tool_span(
        "write_coaching_progress",
        gate_id=result.quality_gate.gate_id,
        support_profile=turn.scaffold_policy.profile,
    ):
        next_check_assistance_level = emitted_assistance_level(
            message=result.message,
            next_prompt=result.quality_gate.next_prompt,
            assistance=result.next_check_assistance,
        )
        return store.record_turn(
            user_id=turn.user_id,
            course_id=turn.course_id,
            lecture_id=turn.lecture_id,
            context=turn.coaching_context,
            policy=turn.scaffold_policy,
            decision=result.quality_gate,
            gate_revision=turn.coaching_context.active_gate_revision,
            user_message=turn.message,
            assistant_message=result.message,
            session_goal=result.session_goal,
            next_check_assistance_level=next_check_assistance_level,
            review_after_days=turn.coaching_context.active_gate_review_after_days or 2,
        )


def enforce_bound_attempt(result: AgentTurnResult, turn: AgentTurnInput) -> AgentTurnResult:
    decision = result.quality_gate
    context = turn.coaching_context
    if (
        decision is None
        or decision.status == QualityGateStatus.NOT_ASSESSED
        or (
            context.pending_check_gate_id == decision.gate_id
            and context.pending_check_gate_revision == decision.gate_revision
            and context.pending_check_issued_at is not None
        )
    ):
        return result
    return result.model_copy(
        update={
            "quality_gate": decision.model_copy(
                update={
                    "status": QualityGateStatus.NOT_ASSESSED,
                    "reason": "The learner message was not an answer to the persisted active check.",
                    "evidence_ids": [],
                    "missing_evidence_ids": [],
                    "next_prompt": decision.next_prompt
                    or "Answer the current check in your own words.",
                }
            )
        }
    )
