from types import SimpleNamespace
import sys

import pytest

from lecturepilot.agent_response_schema import (
    source_routing_response_format,
    source_routing_review_response_format,
)
from lecturepilot.course_source_routing_client import LiteLLMSourceRoutingClient
from lecturepilot.models import ProviderCapability, ProviderSettings


@pytest.mark.asyncio
async def test_source_routing_client_sends_structured_provider_requests(monkeypatch) -> None:
    calls: list[dict] = []

    async def fake_completion(**kwargs):
        calls.append(kwargs)
        content = '{"selections":[]}' if len(calls) == 1 else '{"corrections":[]}'
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
            usage=None,
        )

    monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(acompletion=fake_completion))
    settings = ProviderSettings(
        provider="openai",
        model="openai/gpt-5.6-luna",
        api_key_env="OPENAI_API_KEY",
        capabilities={ProviderCapability.CHAT, ProviderCapability.STRUCTURED_JSON},
    )
    messages = [{"role": "user", "content": "Route these sources."}]
    client = LiteLLMSourceRoutingClient()

    assert await client.complete_routing(settings=settings, messages=messages) == {"selections": []}
    assert await client.review_routing(settings=settings, messages=messages) == {"corrections": []}

    assert [call["response_format"] for call in calls] == [
        source_routing_response_format(),
        source_routing_review_response_format(),
    ]
    for call in calls:
        assert call["model"] == "openai/gpt-5.6-luna"
        assert call["messages"] == messages
        assert call["max_tokens"] == 8000
        assert call["max_retries"] == 0
        assert call["timeout"] == 120
        assert "temperature" not in call
