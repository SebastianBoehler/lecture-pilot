import json
import sys
from types import SimpleNamespace

import pytest

from lecturepilot.model_client import LiteLLMModelClient
from lecturepilot.models import ProviderSettings
from test_strict_model_payload import _payload, _turn


@pytest.mark.asyncio
async def test_checkpoint_uses_one_structured_assessment_without_filesystem_tools(monkeypatch):
    calls = []

    async def completion(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(_payload())))],
        )

    monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(acompletion=completion))
    turn = _turn()
    turn = turn.model_copy(update={"checkpoint_gate_id": turn.active_gate.id})
    result = await LiteLLMModelClient().complete_turn(
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
    assert "tools" not in calls[0]
    assert calls[0]["response_format"]["json_schema"]["strict"] is True
    assert result.quality_gate.status.value == "needs_evidence"
