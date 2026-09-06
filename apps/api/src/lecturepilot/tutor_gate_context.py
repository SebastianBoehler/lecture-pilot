from __future__ import annotations

from lecturepilot.coaching_transitions import CheckTransition, derive_next_transition
from lecturepilot.models import AgentTurnInput
from lecturepilot.quality_gate_models import QualityGateStatus


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
        f"Unfamiliar transfer prompt: {gate.transfer_prompt}\n"
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


def _transition_contract(turn: AgentTurnInput) -> str:
    gate = turn.active_gate
    stage = turn.coaching_context.pending_check_stage
    if gate is None or stage is None:
        return "No bound assessment stage. Do not return a next_check field.\n"
    passed = derive_next_transition(
        gate,
        current_stage=stage,
        status=QualityGateStatus.PASSED,
        exposed_hint_levels=turn.coaching_context.exposed_hint_levels,
        exposed_task_ids=turn.coaching_context.exposed_task_ids,
        current_task_id=turn.coaching_context.pending_check_task_id,
    )
    needs_evidence = derive_next_transition(
        gate,
        current_stage=stage,
        status=QualityGateStatus.NEEDS_EVIDENCE,
        exposed_hint_levels=turn.coaching_context.exposed_hint_levels,
        exposed_task_ids=turn.coaching_context.exposed_task_ids,
        current_task_id=turn.coaching_context.pending_check_task_id,
    )
    return (
        f"Current persisted assessment stage: {stage}\n"
        f"If passed, server-selected next check: {_describe_transition(passed)}\n"
        "If needs_evidence, server-selected next check: "
        f"{_describe_transition(needs_evidence)}\n"
        "These transitions are applied by the server after assessment. "
        "Do not return a next_check field or substitute tasks or support.\n"
    )


def _describe_transition(transition: CheckTransition | None) -> str:
    if transition is None:
        return "null"
    assistance = transition.check.assistance
    return (
        f"stage={transition.stage}; assistance={assistance.level}; "
        f"content={assistance.content!r}; prompt={transition.check.prompt!r}"
    )
