from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI

from lecturepilot.agent_state_access import learner_state_store
from lecturepilot.coaching_progress import CoachingProgressStore, CoachingTurnEvent
from lecturepilot.guided_tutor import LOCAL_PREVIEW_USER_ID
from lecturepilot.learning_gate_selector import select_active_gate
from lecturepilot.learning_gates import gate_spec_for_lecture
from lecturepilot.models import AgentCoachingContext, AgentTurnInput, AgentTurnResult
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
        active_gate = (
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
            context = AgentCoachingContext()
        else:
            with observability.tool_span("read_coaching_progress", gate_id=active_gate.id):
                context = store.context(
                    user_id=turn.user_id,
                    course_id=turn.course_id,
                    lecture_id=turn.lecture_id,
                    gate_id=active_gate.id,
                    gate_title=active_gate.title,
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
            prior_assistance=context.prior_assistance,
        )
    )
    return turn.model_copy(
        update={
            "active_gate": active_gate,
            "coaching_context": context,
            "scaffold_policy": policy,
        },
        deep=True,
    )


def persist_coaching_turn(
    app: FastAPI,
    turn: AgentTurnInput,
    result: AgentTurnResult,
    activity: Callable[[str], None],
    observability: Observability,
) -> CoachingTurnEvent | None:
    if result.quality_gate is None or turn.scaffold_policy is None:
        return None
    activity("save coaching progress")
    with observability.tool_span(
        "write_coaching_progress",
        gate_id=result.quality_gate.gate_id,
        support_profile=turn.scaffold_policy.profile,
    ):
        return CoachingProgressStore(app.state.canvas_workspace.layout).record_turn(
            user_id=turn.user_id,
            course_id=turn.course_id,
            lecture_id=turn.lecture_id,
            context=turn.coaching_context,
            policy=turn.scaffold_policy,
            decision=result.quality_gate,
            session_goal=result.session_goal,
            review_after_days=turn.coaching_context.active_gate_review_after_days or 2,
        )
