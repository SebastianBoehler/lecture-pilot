import json
from types import SimpleNamespace

import pytest

from lecturepilot.agent_response_schema import lecturepilot_response_format
from lecturepilot.agent_tool_loop import complete_tool_turn
from lecturepilot.model_payload import agent_result_from_content
from lecturepilot.models import ProviderSettings
from lecturepilot.observability import Observability
from test_strict_model_payload import _payload, _turn


def test_bound_check_allows_an_unassessed_interruption() -> None:
    payload = _payload()
    payload["assessment"] = None
    payload["next_check"] = None

    result = agent_result_from_content(json.dumps(payload), _turn(), "model")

    assert result.quality_gate is None
    assert result.next_check is None


def test_provider_schema_allows_only_bound_or_null_assessments() -> None:
    bound = lecturepilot_response_format(_turn())["json_schema"]["schema"]
    unbound = lecturepilot_response_format(_turn(bound_check=False))["json_schema"]["schema"]

    assert bound["properties"]["assessment"]["type"] == ["object", "null"]
    assert unbound["properties"]["assessment"] == {"type": "null"}


@pytest.mark.asyncio
async def test_tool_loop_repair_receives_the_exact_contract_error() -> None:
    invalid = _payload()
    invalid["next_check"]["assistance"]["content"] = "This cue is absent."
    corrected = _payload()
    calls: list[dict] = []

    async def completion(**kwargs):
        calls.append(kwargs)
        content = invalid if len(calls) == 1 else corrected
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(content)))]
        )

    class Executor:
        @staticmethod
        def pending_canvas_edit_instruction():
            return None

    result = await complete_tool_turn(
        acompletion=completion,
        settings=ProviderSettings(
            provider="openai",
            model="gpt-5.6-luna",
            api_key_env="OPENAI_API_KEY",
            capabilities=set(),
        ),
        turn=_turn(),
        tool_executor=Executor(),
        observability=Observability(),
        emit=None,
        messages=[{"role": "system", "content": "Tutor."}],
    )

    repair_instruction = calls[1]["messages"][-1]["content"]
    assert "declared next-check assistance is not present" in repair_instruction
    assert result.message == corrected["message"]
