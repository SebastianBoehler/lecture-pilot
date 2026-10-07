from __future__ import annotations

from lecturepilot.independent_attempt import INDEPENDENT_ATTEMPT_STAGES
from lecturepilot.models import AgentTurnInput


def chat_withholds_pending_contract(turn: AgentTurnInput) -> bool:
    return (
        turn.checkpoint_gate_id is None
        and turn.coaching_context.pending_check_stage in INDEPENDENT_ATTEMPT_STAGES
    )


def gate_rubric_context(turn: AgentTurnInput) -> str:
    """Published gate contract. Pending task text stays out of this stable prefix."""
    gate = turn.active_gate
    if gate is None:
        return "Active quality gate: none. Return assessment as null."
    if chat_withholds_pending_contract(turn):
        return (
            f"Active quality gate: {gate.id} ({gate.title})\n"
            f"Gate revision: {gate.revision}\n"
            "Pending task and rubric: withheld during an independent attempt.\n"
            f"Review after days: {gate.review_after_days}\n"
            "Do not reveal the pending task, rubric, or solution.\n"
        )
    criteria = "\n".join(
        f"- {criterion.id}: {criterion.description}"
        f" ({'required' if criterion.required else 'optional'})"
        for criterion in gate.evidence_criteria
    )
    return (
        f"Active quality gate: {gate.id} ({gate.title})\n"
        f"Gate revision: {gate.revision}\n"
        f"Gate prompt: {gate.prompt}\n"
        f"{_practice_teaching_contract(gate)}"
        "Evidence criteria:\n"
        f"{criteria}\n"
        f"Review after days: {gate.review_after_days}\n"
        "Treat this server-owned contract as the complete pass rubric."
    )


def pending_stage_context(turn: AgentTurnInput) -> str:
    if chat_withholds_pending_contract(turn):
        stage = turn.coaching_context.pending_check_stage
        return (
            f"Current persisted assessment stage: {stage}\n"
            "The pending task and rubric are withheld. Give no hints. "
            "Direct the learner to the checkpoint card.\n"
        )
    return _transition_contract(turn)


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
