import json

import pytest

from lecturepilot.agent_response_schema import lecturepilot_response_format
from lecturepilot.native_tutor import native_tutor_turn
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.messages import ModelResponse, TextPart
from lecturepilot.model_payload import agent_result_from_content
from lecturepilot.models import ProviderSettings
from lecturepilot.observability import Observability
from test_strict_model_payload import _payload, _turn


def test_bound_check_allows_an_unassessed_interruption() -> None:
    payload = _payload()
    payload["assessment"] = None

    result = agent_result_from_content(
        json.dumps(payload), _turn().model_copy(update={"checkpoint_gate_id": None}), "model"
    )

    assert result.quality_gate is None
    assert result.next_check is None


def test_provider_schema_allows_only_bound_or_null_assessments() -> None:
    bound = lecturepilot_response_format(_turn())["json_schema"]["schema"]
    unbound = lecturepilot_response_format(_turn(bound_check=False))["json_schema"]["schema"]

    assert bound["properties"]["assessment"]["type"] == "object"
    assert unbound["properties"]["assessment"] == {"type": "null"}
    assert "next_check" not in unbound["properties"]


@pytest.mark.asyncio
async def test_tool_loop_repair_rejects_provider_owned_next_check() -> None:
    invalid = _payload()
    invalid["next_check"] = {"prompt": "An invented replacement check."}
    invalid["message"] = "An invented replacement check."
    corrected = _payload()
    calls: list[dict] = []

    def completion(messages, info):
        calls.append(messages)
        content = invalid if len(calls) == 1 else corrected
        return ModelResponse(parts=[TextPart(json.dumps(content))])

    class Executor:
        @staticmethod
        def pending_canvas_edit_instruction():
            return None

    result = await native_tutor_turn(
        model=FunctionModel(completion),
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
        messages=[{"role": "system", "content": "Tutor."}, {"role": "user", "content": "Answer"}],
    )

    repair_instruction = str(calls[1][-1])
    assert "result contract" in repair_instruction
    assert result.message == (
        "More evidence is needed for the approved criterion: Names one boundary.\n\n"
        "Next check:\nExplain the mechanism."
    )
