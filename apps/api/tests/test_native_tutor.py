import json
from types import SimpleNamespace

from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import FunctionModel

from lecturepilot.native_tutor import native_tutor_turn
from lecturepilot.models import ProviderSettings
from test_strict_model_payload import _payload, _turn


async def test_native_tool_turn_pairs_all_calls_and_uses_strict_final_schema():
    requests, executed = [], []

    def respond(messages, info):
        requests.append((messages, info))
        assert info.model_request_parameters.output_mode == "native"
        assert info.model_settings["openai_reasoning_effort"] == "none"
        if len(requests) == 1:
            return ModelResponse(
                parts=[ToolCallPart("pwd", {}, tool_call_id=str(i)) for i in range(7)]
            )
        replies = [
            part
            for message in messages
            for part in message.parts
            if isinstance(part, ToolReturnPart)
        ]
        assert len(replies) == 7
        assert replies[-1].content["ok"] is False
        return ModelResponse(parts=[TextPart(json.dumps(_payload()))])

    executor = SimpleNamespace(
        execute=lambda name, args: executed.append(name) or {"ok": True},
        pending_canvas_edit_instruction=lambda: None,
    )
    result = await native_tutor_turn(
        settings=ProviderSettings(
            provider="openai", model="openai/gpt-6", api_key_env="KEY", capabilities=set()
        ),
        turn=_turn(),
        messages=[
            {"role": "system", "content": "Tutor rules."},
            {"role": "user", "content": "Student answer"},
        ],
        model=FunctionModel(respond),
        tool_executor=executor,
    )
    assert len(executed) == 6
    assert result.model == "openai/gpt-6"


async def test_native_turn_preserves_history_roles_and_repairs_validation():
    calls = 0

    def respond(messages, info):
        nonlocal calls
        calls += 1
        if calls == 1:
            assert messages[0].kind == "request"
            assert messages[1].kind == "response"
            assert messages[-1].kind == "request"
        payload = _payload()
        if calls == 1:
            payload["canvas_commands"][0]["section_id"] = "invented"
        return ModelResponse(parts=[TextPart(json.dumps(payload))])

    await native_tutor_turn(
        settings=ProviderSettings(
            provider="openai", model="openai/gpt-6", api_key_env="KEY", capabilities=set()
        ),
        turn=_turn(),
        messages=[
            {"role": "system", "content": "Tutor rules."},
            {"role": "user", "content": "Canvas"},
            {"role": "assistant", "content": "Previous reply"},
            {"role": "user", "content": "Student answer"},
        ],
        model=FunctionModel(respond),
    )
    assert calls == 2
