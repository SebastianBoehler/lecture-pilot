from __future__ import annotations

import json
import sys
from types import SimpleNamespace

import pytest

from lecturepilot.learning_map import LearningMapGate
from lecturepilot.model_client import LiteLLMModelClient, ModelExecutionError
from lecturepilot.models import AgentTurnInput, AttendanceStatus, CanvasState, ProviderSettings
from lecturepilot.providers import ProviderConfigurationError


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
                                "message": (
                                    "Remember that likelihood conditions on the hypothesis. "
                                    "Explain the likelihood term."
                                ),
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
                                "next_check_assistance": {
                                    "level": "cue",
                                    "content": "Remember that likelihood conditions on the hypothesis.",
                                },
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
            model="gemini/test-model",
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
            active_gate=LearningMapGate(
                id="bayes-decision-check",
                concept_id="bayes-decision",
                title="Bayes decision",
                prompt="Explain the likelihood term.",
                section_id="bayes-formula",
            ),
        ),
    )

    assert result.message == (
        "Remember that likelihood conditions on the hypothesis. Explain the likelihood term."
    )
    assert result.session_goal == "Apply Bayes to a new decision."
    assert result.model_dump().get("next_check_assistance") == {
        "level": "cue",
        "content": "Remember that likelihood conditions on the hypothesis.",
    }
    assert calls[0]["response_format"]["type"] == "json_schema"
    schema = calls[0]["response_format"]["json_schema"]["schema"]
    assert calls[0]["response_format"]["json_schema"]["strict"] is True
    assert schema["required"] == [
        "message",
        "session_goal",
        "canvas_commands",
        "next_check_assistance",
        "quality_gate",
    ]
    block_schema = schema["properties"]["canvas_commands"]["items"]["properties"]["section"][
        "properties"
    ]["blocks"]["items"]
    assert block_schema["properties"]["component_type"]["enum"] == [
        "single_choice_quiz",
        "interactive_chart",
        "process_explorer",
        None,
    ]
    assert calls[0]["temperature"] == 0.3


async def test_model_client_preserves_payload_contract_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_completion(**kwargs):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="not json"))]
        )

    monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(acompletion=fake_completion))

    with pytest.raises(ProviderConfigurationError, match="valid LecturePilot JSON"):
        await LiteLLMModelClient().complete_turn(
            settings=ProviderSettings(
                provider="gemini",
                model="gemini/test-model",
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
            model="openai/gpt-5.6-luna",
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


async def test_model_client_reports_exhausted_openai_credits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_completion(**_kwargs):
        raise _QuotaError(
            "You have no credits remaining.",
            code="credit_balance_exhausted",
        )

    monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(acompletion=fake_completion))

    with pytest.raises(
        ModelExecutionError,
        match="OpenAI API credits are exhausted.*retry this tutor message",
    ):
        await LiteLLMModelClient().complete_turn(
            settings=ProviderSettings(
                provider="openai",
                model="openai/gpt-5.6-luna",
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


async def test_model_client_uses_selected_learning_map_gate_contract(
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
                                "message": "Try the transfer boundary.",
                                "session_goal": None,
                                "canvas_commands": [],
                                "quality_gate": {
                                    "gate_id": "causal-transfer-check",
                                    "status": "not_assessed",
                                    "reason": "No answer yet.",
                                    "next_prompt": "Name the transfer boundary.",
                                    "evidence_ids": [],
                                    "missing_evidence_ids": [],
                                },
                            }
                        )
                    )
                )
            ]
        )

    monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(acompletion=fake_completion))
    gate = LearningMapGate(
        id="causal-transfer-check",
        concept_id="causal-transfer",
        title="Causal transfer",
        prompt="Explain when the conclusion transfers.",
        evidence_criteria=[{"id": "boundary", "description": "Name a transfer boundary."}],
        transfer_prompt="Apply this to an unfamiliar hospital setting.",
        section_id="causal-transfer",
    )

    await LiteLLMModelClient().complete_turn(
        settings=ProviderSettings(
            provider="gemini",
            model="gemini/test-model",
            api_key_env="GEMINI_API_KEY",
            capabilities=set(),
        ),
        turn=AgentTurnInput(
            user_id="u1",
            course_id="course-1",
            lecture_id="lecture-14",
            attendance=AttendanceStatus.PRESENT,
            message="Help me check transfer.",
            active_gate=gate,
        ),
    )

    prompt = "\n".join(message["content"] for message in calls[0]["messages"])
    assert "Active quality gate: causal-transfer-check (Causal transfer)" in prompt
    assert "boundary: Name a transfer boundary." in prompt
    assert "Apply this to an unfamiliar hospital setting." in prompt
    assert "definition, mechanism, computation" not in prompt


class _QuotaError(RuntimeError):
    status_code = 429

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code
