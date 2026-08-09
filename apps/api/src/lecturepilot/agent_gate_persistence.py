from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI

from lecturepilot.agent_state_access import analytics_store, learner_state_store
from lecturepilot.coaching_progress import CoachingTurnEvent
from lecturepilot.guided_tutor import LOCAL_PREVIEW_USER_ID
from lecturepilot.models import AssessedAgentTurnInput, AgentTurnInput, AgentTurnResult
from lecturepilot.observability import Observability
from lecturepilot.professor_preview import is_professor_preview_user_id


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
        if turn.user_id == LOCAL_PREVIEW_USER_ID or is_professor_preview_user_id(turn.user_id):
            return
        assessed_turn = AssessedAgentTurnInput.model_validate(turn.model_dump())
        store = analytics_store(app)
        store.record_quality_gate(
            course_id=assessed_turn.course_id,
            lecture_id=assessed_turn.lecture_id,
            user_id=assessed_turn.user_id,
            attendance=assessed_turn.attendance,
            decision=decision,
            publication_version=assessed_turn.analytics_context.publication_version,
            learning_map_revision=assessed_turn.analytics_context.learning_map_revision,
            coaching_event=coaching_event,
        )
