from __future__ import annotations

import json

from pydantic import ValidationError

from lecturepilot.assessment_feedback import assessment_reason, compose_assessment_message
from lecturepilot.model_commands import (
    checkpoint_assessment_required,
    resolve_provider_canvas_commands,
    select_next_check,
    validate_quality_gate_decision,
)
from lecturepilot.models import (
    AgentTurnInput,
    AgentTurnResult,
    QualityGateDecision,
    QualityGateStatus,
)
from lecturepilot.provider_turn_result import ProviderAgentTurnResult, ProviderQualityGateDecision
from lecturepilot.providers import ProviderConfigurationError


def agent_result_from_content(
    content: str | None,
    turn: AgentTurnInput,
    model: str,
) -> AgentTurnResult:
    payload = parse_model_payload(content)
    try:
        provider_result = ProviderAgentTurnResult.model_validate(payload)
    except ValidationError as exc:
        raise ProviderConfigurationError(
            "Model response violates the tutor result contract."
        ) from exc
    commands = resolve_provider_canvas_commands(
        [command.to_domain() for command in provider_result.canvas_commands], turn
    )
    decision = _quality_gate_decision(provider_result.assessment, turn)
    if decision is None and checkpoint_assessment_required(turn):
        raise ProviderConfigurationError("Explicit checkpoint submission requires an assessment.")
    decision = validate_quality_gate_decision(decision, turn)
    next_check = select_next_check(turn, decision)
    message = provider_result.message.strip()
    if decision is not None:
        message = compose_assessment_message(decision, next_check)
    result = AgentTurnResult(
        message=message,
        session_goal=(
            provider_result.session_goal.strip() if provider_result.session_goal else None
        ),
        canvas_commands=commands,
        next_check=next_check,
        quality_gate=decision,
        model=model,
    )
    return result


def _quality_gate_decision(
    assessment: ProviderQualityGateDecision | None, turn: AgentTurnInput
) -> QualityGateDecision | None:
    if assessment is None:
        return None
    gate = turn.active_gate
    required = [
        criterion.id for criterion in (gate.evidence_criteria if gate else []) if criterion.required
    ]
    missing = [
        evidence_id for evidence_id in required if evidence_id not in assessment.evidence_ids
    ]
    return QualityGateDecision(
        **assessment.model_dump(mode="json", exclude={"reason"}),
        reason=(assessment_reason(gate, missing) if gate is not None else assessment.reason),
        status=(QualityGateStatus.NEEDS_EVIDENCE if missing else QualityGateStatus.PASSED),
        missing_evidence_ids=missing,
    )


def parse_model_payload(content: str | None) -> dict:
    if not content:
        raise ProviderConfigurationError("Model returned an empty response.")
    cleaned = content.strip()
    if cleaned.startswith("```"):
        raise ProviderConfigurationError("Model JSON must be a plain object without code fences.")
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ProviderConfigurationError("Model did not return valid LecturePilot JSON.") from exc
    if not isinstance(payload, dict):
        raise ProviderConfigurationError("Model JSON must be an object.")
    return payload
