from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI

from lecturepilot.coaching_progress import CoachingProgressStore
from lecturepilot.learning_gates import gate_spec_for_lecture
from lecturepilot.models import AgentTurnInput, AgentTurnResult
from lecturepilot.observability import Observability
from lecturepilot.scaffold_policy import scaffold_policy_for_tutor_turn


def prepare_coaching_turn(
    app: FastAPI,
    turn: AgentTurnInput,
    activity: Callable[[str], None],
    observability: Observability,
) -> AgentTurnInput:
    activity("load coaching progress")
    spec = gate_spec_for_lecture(turn.lecture_id)
    store = CoachingProgressStore(app.state.canvas_workspace.layout)
    with observability.tool_span("read_coaching_progress", gate_id=spec.gate_id):
        context = store.context(
            user_id=turn.user_id,
            course_id=turn.course_id,
            lecture_id=turn.lecture_id,
            gate_id=spec.gate_id,
            gate_title=spec.title,
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
        update={"coaching_context": context, "scaffold_policy": policy},
        deep=True,
    )


def persist_coaching_turn(
    app: FastAPI,
    turn: AgentTurnInput,
    result: AgentTurnResult,
    activity: Callable[[str], None],
    observability: Observability,
) -> None:
    if result.quality_gate is None or turn.scaffold_policy is None:
        return
    activity("save coaching progress")
    with observability.tool_span(
        "write_coaching_progress",
        gate_id=result.quality_gate.gate_id,
        support_profile=turn.scaffold_policy.profile,
    ):
        CoachingProgressStore(app.state.canvas_workspace.layout).record_turn(
            user_id=turn.user_id,
            course_id=turn.course_id,
            lecture_id=turn.lecture_id,
            context=turn.coaching_context,
            policy=turn.scaffold_policy,
            decision=result.quality_gate,
            session_goal=result.session_goal,
        )
