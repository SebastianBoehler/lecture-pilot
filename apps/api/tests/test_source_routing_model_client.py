import json
from pydantic_ai.messages import ModelResponse, TextPart
from pydantic_ai.models.function import FunctionModel

from lecturepilot.course_source_routing_client import NativeSourceRoutingClient
from lecturepilot.models import ProviderSettings


async def test_source_routing_client_sends_native_strict_schema_requests():
    calls = []

    def respond(messages, info):
        calls.append(info)
        payload = {"selections": []} if len(calls) == 1 else {"corrections": []}
        return ModelResponse(parts=[TextPart(json.dumps(payload))])

    settings = ProviderSettings(
        provider="openai",
        model="openai/gpt-5.6-luna",
        api_key_env="OPENAI_API_KEY",
        capabilities=set(),
    )
    client = NativeSourceRoutingClient(model=FunctionModel(respond))
    messages = [{"role": "user", "content": "Route these sources."}]
    assert await client.complete_routing(settings=settings, messages=messages) == {"selections": []}
    assert await client.review_routing(settings=settings, messages=messages) == {"corrections": []}
    for info in calls:
        assert info.model_settings["max_tokens"] == 8000
        assert info.model_settings["timeout"] == 120
        assert info.model_settings["openai_reasoning_effort"] == "low"
        assert info.model_settings["openai_store"] is False
