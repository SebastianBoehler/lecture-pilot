from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI

from lecturepilot.agent_state_access import analytics_store, learner_state_store
from lecturepilot.coaching_progress import CoachingTurnEvent
from lecturepilot.models import AgentTurnInput, AgentTurnResult
from lecturepilot.observability import Observability


def persist_quality_gate(
    app: FastAPI,
    *,
    turn: AgentTurnInput,
    result: AgentTurnResult,
    activity: Callable[[str], None],
    observability: Observability,
    coaching_event: CoachingTurnEvent | None,
) -> None:
    decision = result.quality_gate
    if (
        decision is None
        or not turn.course_id
        or coaching_event is None
        or coaching_event.attempt_kind == "none"
    ):
        return
    activity("save quality gate")
    with observability.tool_span(
        "record_quality_gate", gate_id=decision.gate_id, status=decision.status.value
    ):
        learner_state_store(app).record_quality_gate(
            course_id=turn.course_id,
            lecture_id=turn.lecture_id,
            user_id=turn.user_id,
            decision=decision,
        )
        if (store := analytics_store(app)) is not None:
            store.record_quality_gate(
                course_id=turn.course_id,
                lecture_id=turn.lecture_id,
                user_id=turn.user_id,
                attendance=turn.attendance,
                decision=decision,
                coaching_event=coaching_event,
            )
