from __future__ import annotations

import json

from lecturepilot.coaching_assistance import NextCheckAssistance, emitted_assistance_level
from lecturepilot.model_commands import read_canvas_commands, read_quality_gate
from lecturepilot.models import AgentTurnInput, AgentTurnResult
from lecturepilot.providers import ProviderConfigurationError


def agent_result_from_content(
    content: str | None,
    turn: AgentTurnInput,
    model: str,
) -> AgentTurnResult:
    payload = parse_model_payload(content)
    result = AgentTurnResult(
        message=read_message(payload),
        session_goal=read_session_goal(payload),
        canvas_commands=read_canvas_commands(payload, turn),
        next_check_assistance=NextCheckAssistance.model_validate(
            payload.get("next_check_assistance", {})
        ),
        quality_gate=read_quality_gate(payload, turn),
        model=model,
    )
    try:
        emitted_assistance_level(
            message=result.message,
            next_prompt=(result.quality_gate.next_prompt if result.quality_gate else None),
            assistance=result.next_check_assistance,
        )
    except ValueError as exc:
        raise ProviderConfigurationError(f"Invalid next-check assistance: {exc}.") from exc
    return result


def parse_model_payload(content: str | None) -> dict:
    if not content:
        raise ProviderConfigurationError("Model returned an empty response.")
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").removeprefix("json").strip()
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ProviderConfigurationError("Model did not return valid LecturePilot JSON.") from exc
    if not isinstance(payload, dict):
        raise ProviderConfigurationError("Model JSON must be an object.")
    return payload


def read_message(payload: dict) -> str:
    message = payload.get("message")
    if not isinstance(message, str) or not message.strip():
        raise ProviderConfigurationError("Model JSON must include a non-empty message.")
    return message.strip()


def read_session_goal(payload: dict) -> str | None:
    goal = payload.get("session_goal")
    return goal.strip() if isinstance(goal, str) and goal.strip() else None
