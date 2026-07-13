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
                                "session_goal": "Apply Bayes to a new decision.",
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
    assert result.session_goal == "Apply Bayes to a new decision."
    assert calls[0]["response_format"]["type"] == "json_schema"
    schema = calls[0]["response_format"]["json_schema"]["schema"]
    assert calls[0]["response_format"]["json_schema"]["strict"] is True
    assert schema["required"] == ["message", "session_goal", "canvas_commands", "quality_gate"]
    assert calls[0]["temperature"] == 0.3


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


async def test_model_client_omits_temperature_for_openai_gpt5(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []

    async def fake_completion(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=json.dumps(
                            {
                                "message": "OpenAI response.",
                                "canvas_commands": [],
                                "quality_gate": {
                                    "gate_id": "lecture-learning-outcome-check",
                                    "status": "not_assessed",
                                    "reason": "Provider compatibility check.",
                                    "next_prompt": None,
                                },
                            }
                        )
                    )
                )
            ]
        )

    monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(acompletion=fake_completion))

    await LiteLLMModelClient().complete_turn(
        settings=ProviderSettings(
            provider="openai",
            model="openai/gpt-5-mini",
            api_key_env="OPENAI_API_KEY",
            capabilities=set(),
        ),
        turn=AgentTurnInput(
            user_id="u1",
            course_id="course-1",
            lecture_id="lecture-01",
            attendance=AttendanceStatus.UNKNOWN,
            message="Explain the topic.",
        ),
    )

    assert "temperature" not in calls[0]
    assert calls[0]["reasoning_effort"] == "low"
