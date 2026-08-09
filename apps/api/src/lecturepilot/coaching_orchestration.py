from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException

from lecturepilot.agent_state_access import learner_state_store
from lecturepilot.coaching_progress import CoachingProgressStore, CoachingTurnEvent
from lecturepilot.coaching_state_models import CoachingProgress, review_key
from lecturepilot.learning_gate_selector import select_active_gate
from lecturepilot.learning_map import LearningMap, LearningMapGate
from lecturepilot.models import (
    AgentCoachingContext,
    AgentAnalyticsContext,
    AgentTurnInput,
    AgentTurnResult,
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
    analytics_context = app.state.canvas_workspace.course_canvas_store.read_analytics_context(
        course_id=turn.course_id, lecture_id=turn.lecture_id
    )
    learning_map = analytics_context.learning_map
    turn_analytics = AgentAnalyticsContext(
        publication_version=analytics_context.publication_version,
        learning_map_revision=analytics_context.learning_map_revision,
    )
    decisions = learner_state_store(app).latest_gate_decisions(
        user_id=turn.user_id,
        course_id=turn.course_id,
        lecture_id=turn.lecture_id,
    )
    if turn.checkpoint_gate_id is not None:
        _validate_requested_gate(
            learning_map,
            requested_gate_id=turn.checkpoint_gate_id,
            focused_section_id=turn.canvas_state.focused_section_id,
            require_focused_section=True,
        )
        active_gate = next(
            gate for gate in learning_map.gates if gate.id == turn.checkpoint_gate_id
        )
        store.bind_inline_checkpoint(
            user_id=turn.user_id,
            course_id=turn.course_id,
            lecture_id=turn.lecture_id,
            gate_id=active_gate.id,
            gate_revision=active_gate.revision,
            published_prompt=active_gate.prompt,
        )
    else:
        if turn.requested_gate_id is not None:
            _validate_requested_gate(
                learning_map,
                requested_gate_id=turn.requested_gate_id,
                focused_section_id=turn.canvas_state.focused_section_id,
            )
        active_gate = select_due_review_gate(learning_map, progress) or select_active_gate(
            learning_map,
            requested_gate_id=turn.requested_gate_id,
            focused_section_id=turn.canvas_state.focused_section_id,
            latest_decisions=decisions,
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
                gate_revision=active_gate.revision,
                learning_objective=learning_map.objective,
            )
        context = context.model_copy(
            update={
                "active_gate_id": active_gate.id,
                "active_gate_revision": active_gate.revision,
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
            "analytics_context": turn_analytics,
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
    candidates: list[tuple[datetime, LearningMapGate]] = []
    for gate in learning_map.gates:
        review = progress.delayed_reviews.get(review_key(gate.id, gate.revision))
        if review is None or review.completed_at is not None or review.attempted_at is not None:
            continue
        due_at = review.due_at
        if due_at <= current_time:
            candidates.append((due_at, gate))
    pending = progress.pending_check
    if pending is not None and pending.kind == "delayed_transfer":
        opened = next(
            (
                gate
                for _, gate in candidates
                if gate.id == pending.gate_id and gate.revision == pending.gate_revision
            ),
            None,
        )
        if opened is not None:
            return opened
    return min(candidates, key=lambda item: (item[0], item[1].id))[1] if candidates else None


def _validate_requested_gate(
    learning_map: LearningMap | None,
    *,
    requested_gate_id: str,
    focused_section_id: str | None,
    require_focused_section: bool = False,
) -> None:
    gate = (
        next(
            (gate for gate in learning_map.gates if gate.id == requested_gate_id),
            None,
        )
        if learning_map is not None
        else None
    )
    if gate is None:
        raise HTTPException(
            status_code=400,
            detail="Requested checkpoint is not in the published learning map.",
        )
    if (require_focused_section or focused_section_id is not None) and (
        focused_section_id != gate.section_id
    ):
        raise HTTPException(
            status_code=400,
            detail="Requested checkpoint does not belong to the focused section.",
        )


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
            next_check=result.next_check,
            session_goal=result.session_goal,
        )
        return None
    activity("save coaching progress")
    with observability.tool_span(
        "write_coaching_progress",
        gate_id=result.quality_gate.gate_id,
        support_profile=turn.scaffold_policy.profile,
    ):
        active_gate = turn.active_gate
        if active_gate is None:
            raise ValueError("Assessment requires an active published gate.")
        return store.record_turn(
            user_id=turn.user_id,
            course_id=turn.course_id,
            lecture_id=turn.lecture_id,
            context=turn.coaching_context,
            policy=turn.scaffold_policy,
            decision=result.quality_gate,
            next_check=result.next_check,
            gate_section_id=active_gate.section_id,
            transfer_prompt=active_gate.transfer_prompt,
            review_after_days=active_gate.review_after_days,
            user_message=turn.message,
            assistant_message=result.message,
            session_goal=result.session_goal,
        )
