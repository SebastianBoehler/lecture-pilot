from __future__ import annotations

import json
from typing import Protocol

from lecturepilot.models import (
    AgentTurnInput,
    AgentTurnResult,
    CanvasCommand,
    ProviderSettings,
    QualityGateDecision,
    QualityGateStatus,
)
from lecturepilot.providers import ProviderConfigurationError


class ModelExecutionError(RuntimeError):
    """Raised when the configured model provider rejects or fails a request."""


_SECTIONS = {
    "learning-goals",
    "feature-maps",
    "kernel-trick",
    "skill-check",
    "failure-mode",
}


class ModelClient(Protocol):
    async def complete_turn(
        self,
        *,
        settings: ProviderSettings,
        turn: AgentTurnInput,
    ) -> AgentTurnResult:
        """Complete one tutor turn."""


class LiteLLMModelClient:
    async def complete_turn(
        self,
        *,
        settings: ProviderSettings,
        turn: AgentTurnInput,
    ) -> AgentTurnResult:
        try:
            from litellm import acompletion
        except ImportError as exc:
            raise ProviderConfigurationError(
                'litellm is not installed. Install the backend with the "agent" extra.'
            ) from exc

        try:
            response = await acompletion(
                model=settings.model,
                messages=_messages(turn),
                temperature=0.3,
            )
        except Exception as exc:
            raise ModelExecutionError(
                "Model request failed. Check the provider key and model configuration."
            ) from exc
        payload = _parse_model_payload(response.choices[0].message.content)
        message = _read_message(payload)
        section_id = _read_section_id(payload, turn)
        quality_gate = _read_quality_gate(payload)

        return AgentTurnResult(
            message=message,
            canvas_commands=[CanvasCommand(type="focus_section", section_id=section_id)],
            quality_gate=quality_gate,
            model=settings.model,
        )


def _messages(turn: AgentTurnInput) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You are LecturePilot, a text-first university tutor. "
                "Lead the tutoring flow from the current lecture canvas. "
                "Do not ask open-ended preference questions such as what the student wants. "
                "Use one concrete next check or instruction per turn. "
                "Decide whether the active quality gate passed, needs_evidence, or was not_assessed. "
                "Return only JSON with keys message, focus_section_id, and quality_gate. "
                "focus_section_id must be one of: learning-goals, feature-maps, "
                "kernel-trick, skill-check, failure-mode. "
                "quality_gate must be an object with gate_id, status, reason, and next_prompt. "
                "For this lecture the main gate is kernel-skill-check."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Attendance: {turn.attendance.value}\n"
                f"Current section: {turn.canvas_state.focused_section_id or 'feature-maps'}\n"
                f"Student message: {turn.message}"
            ),
        },
    ]


def _parse_model_payload(content: str | None) -> dict:
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


def _read_message(payload: dict) -> str:
    message = payload.get("message")
    if not isinstance(message, str) or not message.strip():
        raise ProviderConfigurationError("Model JSON must include a non-empty message.")
    return message.strip()


def _read_section_id(payload: dict, turn: AgentTurnInput) -> str:
    requested = payload.get("focus_section_id")
    if isinstance(requested, str) and requested in _SECTIONS:
        return requested
    current = turn.canvas_state.focused_section_id
    return current if current in _SECTIONS else "feature-maps"


def _read_quality_gate(payload: dict) -> QualityGateDecision:
    raw_gate = payload.get("quality_gate")
    if not isinstance(raw_gate, dict):
        return QualityGateDecision(
            gate_id="kernel-skill-check",
            status=QualityGateStatus.NOT_ASSESSED,
            reason="The model did not return a quality gate decision.",
            next_prompt="Answer the current skill check in one sentence.",
        )
    try:
        return QualityGateDecision.model_validate(raw_gate)
    except ValueError as exc:
        raise ProviderConfigurationError("Model returned an invalid quality_gate.") from exc
