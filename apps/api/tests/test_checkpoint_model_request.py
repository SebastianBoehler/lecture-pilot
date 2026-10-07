import json

import pytest

from lecturepilot.model_client import NativeModelClient
from lecturepilot.models import ProviderSettings
from test_strict_model_payload import _payload, _turn


@pytest.mark.asyncio
async def test_checkpoint_uses_one_structured_assessment_without_filesystem_tools(monkeypatch):
    calls = []

    from pydantic_ai.models.function import FunctionModel
    from pydantic_ai.messages import ModelResponse, TextPart

    def completion(messages, info):
        calls.append(info)
        return ModelResponse(parts=[TextPart(json.dumps(_payload()))])

    turn = _turn()
    turn = turn.model_copy(update={"checkpoint_gate_id": turn.active_gate.id})
    result = await NativeModelClient(model=FunctionModel(completion)).complete_turn(
        settings=ProviderSettings(
            provider="openai",
            model="gpt-5.6-luna",
            api_key_env="OPENAI_API_KEY",
            capabilities=set(),
        ),
        turn=turn,
        tool_executor=object(),
    )

    assert len(calls) == 1
    assert calls[0].function_tools == []
    assert calls[0].model_request_parameters.output_object.strict is True
    assert result.quality_gate.status.value == "needs_evidence"
