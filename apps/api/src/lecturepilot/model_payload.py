from __future__ import annotations

import json

from pydantic import ValidationError

from lecturepilot.coaching_assistance import emitted_assistance_level
from lecturepilot.model_commands import (
    validate_provider_canvas_commands,
    validate_next_check,
    validate_quality_gate_decision,
)
from lecturepilot.models import (
    AgentTurnInput,
    AgentTurnResult,
    QualityGateDecision,
    QualityGateStatus,
)
from lecturepilot.provider_turn_result import ProviderAgentTurnResult
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
    commands = [command.to_domain() for command in provider_result.canvas_commands]
    validate_provider_canvas_commands(commands, turn)
    decision = (
        QualityGateDecision(
            **provider_result.assessment.model_dump(mode="json", exclude={"status"}),
            status=QualityGateStatus(provider_result.assessment.status),
        )
        if provider_result.assessment is not None
        else None
    )
    decision = validate_quality_gate_decision(decision, turn)
    validate_next_check(provider_result.next_check, turn)
    result = AgentTurnResult(
        message=provider_result.message.strip(),
        session_goal=(
            provider_result.session_goal.strip() if provider_result.session_goal else None
        ),
        canvas_commands=commands,
        next_check=provider_result.next_check,
        quality_gate=decision,
        model=model,
    )
    try:
        if result.next_check is not None:
            emitted_assistance_level(
                message=result.message,
                prompt=result.next_check.prompt,
                assistance=result.next_check.assistance,
            )
    except ValueError as exc:
        raise ProviderConfigurationError(f"Invalid next-check assistance: {exc}.") from exc
    return result


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
