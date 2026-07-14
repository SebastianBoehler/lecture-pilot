from __future__ import annotations

from lecturepilot.models import AgentTurnResult, QualityGateStatus

_CANVAS_ACTION_TERMS = (
    "add",
    "append",
    "create",
    "edit",
    "extend",
    "focus",
    "generate",
    "highlight",
    "insert",
    "update",
    "write",
)


def keep_canvas_actions_from_passing_gate(
    result: AgentTurnResult, student_message: str
) -> AgentTurnResult:
    gate = result.quality_gate
    if gate is None or gate.status != QualityGateStatus.PASSED:
        return result
    if not any(term in student_message.casefold() for term in _CANVAS_ACTION_TERMS):
        return result
    gate = gate.model_copy(
        update={
            "status": QualityGateStatus.NOT_ASSESSED,
            "reason": "The turn changed or navigated the canvas; it did not provide learner evidence.",
            "next_prompt": gate.next_prompt or "Answer the current check in your own words.",
        }
    )
    return result.model_copy(update={"quality_gate": gate})
