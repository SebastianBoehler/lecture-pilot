from __future__ import annotations

from lecturepilot.models import AgentTurnInput


def gate_rubric_context(turn: AgentTurnInput) -> str:
    gate = turn.active_gate
    if gate is None:
        return "Active quality gate: none. Return assessment as null."
    criteria = "\n".join(
        f"- {criterion.id}: {criterion.description}"
        f" ({'required' if criterion.required else 'optional'})"
        for criterion in gate.evidence_criteria
    )
    teaching_contract = _practice_teaching_contract(gate)
    transition_contract = _transition_contract(turn)
    return (
        f"Active quality gate: {gate.id} ({gate.title})\n"
        f"Gate revision: {gate.revision}\n"
        f"Gate prompt: {turn.coaching_context.pending_check_prompt or gate.prompt}\n"
        f"{teaching_contract}"
        "Evidence criteria:\n"
        f"{criteria}\n"
        f"Review after days: {gate.review_after_days}\n"
        f"{transition_contract}"
        "Treat this server-owned contract as the complete pass rubric."
    )


def _practice_teaching_contract(gate) -> str:
    if gate.practice_target_id is None:
        return ""
    misconceptions = "\n".join(
        f"- {item.id}: {item.description} Diagnostic cue: {item.diagnostic_cue}"
        for item in gate.misconceptions
    )
    return (
        f"Target invariant: {gate.target_invariant}\n"
        "Approved misconceptions:\n"
        f"{misconceptions or '- none'}\n"
    )


def _transition_contract(turn: AgentTurnInput) -> str:
    gate = turn.active_gate
    stage = turn.coaching_context.pending_check_stage
    if gate is None or stage is None:
        return "No bound assessment stage. Do not return a next_check field.\n"
    return (
        f"Current persisted assessment stage: {stage}\n"
        "Judge each rubric criterion from the actual attempt. The server selects the next "
        "approved task and unexposed support after assessment. "
        "Do not invent tasks or support, infer stable learner ability, or return next_check.\n"
    )
