from __future__ import annotations

import json
import sys
from types import SimpleNamespace

import pytest

from lecturepilot.model_client import LiteLLMModelClient
from lecturepilot.models import AgentTurnInput, AttendanceStatus, CanvasState, ProviderSettings
from lecturepilot.providers import DEFAULT_MODEL, ProviderConfigurationError


async def test_model_client_requests_structured_json(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    async def fake_completion(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=json.dumps(
                            {
                                "message": "Structured response.",
                                "canvas_commands": [
                                    {
                                        "type": "focus_section",
                                        "section_id": "bayes-formula",
                                        "span_id": None,
                                        "highlight_text": None,
                                        "artifact_id": None,
                                        "section": None,
                                    }
                                ],
                                "quality_gate": {
                                    "gate_id": "bayes-decision-check",
                                    "status": "needs_evidence",
                                    "reason": "Needs a worked example.",
                                    "next_prompt": "Explain the likelihood term.",
                                },
                            }
                        )
                    )
                )
            ]
        )

    monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(acompletion=fake_completion))

    result = await LiteLLMModelClient().complete_turn(
        settings=ProviderSettings(
            provider="gemini",
            model=DEFAULT_MODEL,
            api_key_env="GEMINI_API_KEY",
            capabilities=set(),
        ),
        turn=AgentTurnInput(
            user_id="u1",
            course_id="martius-ml",
            lecture_id="lecture-03",
            attendance=AttendanceStatus.PRESENT,
            message="Explain Bayes.",
            canvas_state=CanvasState(focused_section_id="bayes-formula"),
        ),
    )

    assert result.message == "Structured response."
    assert calls[0]["response_format"]["type"] == "json_schema"
    schema = calls[0]["response_format"]["json_schema"]["schema"]
    assert calls[0]["response_format"]["json_schema"]["strict"] is True
    assert schema["required"] == ["message", "canvas_commands", "quality_gate"]


async def test_model_client_preserves_payload_contract_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_completion(**kwargs):
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="not json"))])

    monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(acompletion=fake_completion))

    with pytest.raises(ProviderConfigurationError, match="valid LecturePilot JSON"):
        await LiteLLMModelClient().complete_turn(
            settings=ProviderSettings(
                provider="gemini",
                model=DEFAULT_MODEL,
                api_key_env="GEMINI_API_KEY",
                capabilities=set(),
            ),
            turn=AgentTurnInput(
                user_id="u1",
                course_id="martius-ml",
                lecture_id="lecture-03",
                attendance=AttendanceStatus.PRESENT,
                message="Explain Bayes.",
                canvas_state=CanvasState(focused_section_id="bayes-formula"),
            ),
        )
