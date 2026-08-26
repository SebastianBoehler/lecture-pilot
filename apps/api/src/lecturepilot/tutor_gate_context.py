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
    return (
        f"Active quality gate: {gate.id} ({gate.title})\n"
        f"Gate revision: {gate.revision}\n"
        f"Gate prompt: {gate.prompt}\n"
        f"{teaching_contract}"
        "Evidence criteria:\n"
        f"{criteria}\n"
        f"Unfamiliar transfer prompt: {gate.transfer_prompt}\n"
        f"Review after days: {gate.review_after_days}\n"
        "Treat this server-owned contract as the complete pass rubric."
    )


def _practice_teaching_contract(gate) -> str:
    if gate.practice_target_id is None:
        return ""
    misconceptions = "\n".join(
        f"- {item.id}: {item.description} Diagnostic cue: {item.diagnostic_cue}"
        for item in gate.misconceptions
    )
    hints = "\n".join(f"- {item.level}: {item.content}" for item in gate.hint_ladder)
    return (
        f"Target invariant: {gate.target_invariant}\n"
        f"Independent exit task: {gate.independent_exit_task}\n"
        f"Independent exit surface change: {gate.independent_exit_surface_change}\n"
        f"Delayed transfer surface change: {gate.delayed_transfer_surface_change}\n"
        "Approved misconceptions:\n"
        f"{misconceptions or '- none'}\n"
        "Approved hint ladder:\n"
        f"{hints or '- none'}\n"
    )
