import json
import logging
from types import SimpleNamespace

import pytest
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.usage import RequestUsage

from lecturepilot.metadata_events import LOGGER_NAME
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.models import ProviderSettings
from lecturepilot.native_tutor import native_tutor_turn
from test_strict_model_payload import _payload, _turn

SETTINGS = ProviderSettings(
    provider="openai", model="openai/gpt-6", api_key_env="KEY", capabilities=set()
)
EXECUTOR = SimpleNamespace(
    execute=lambda name, args: {"ok": True}, pending_canvas_edit_instruction=lambda: None
)


def _chat_turn(message: str):
    return _turn(bound_check=False).model_copy(update={"message": message})


def _final():
    payload = _payload()
    payload["assessment"] = None
    return ModelResponse(
        parts=[TextPart(json.dumps(payload))],
        usage=RequestUsage(input_tokens=1_200, cache_read_tokens=1_024, output_tokens=40),
    )


async def _run(respond, message="Why does this hold?"):
    return await native_tutor_turn(
        settings=SETTINGS,
        turn=_chat_turn(message),
        messages=[{"role": "system", "content": "Tutor."}, {"role": "user", "content": "Hi"}],
        model=FunctionModel(respond),
        tool_executor=EXECUTOR,
    )


@pytest.mark.parametrize(
    ("message", "max_tokens"),
    [("Why does this hold?", 2_048), ("Please add a summary section to the canvas.", 8_192)],
)
async def test_output_cap_follows_the_turn_intent(message, max_tokens):
    seen = []

    def respond(messages, info):
        seen.append(info.model_settings["max_tokens"])
        return _final()

    await _run(respond, message)
    assert seen == [max_tokens]


async def test_tool_loop_stops_after_four_model_requests():
    requests = 0

    def respond(messages, info):
        nonlocal requests
        requests += 1
        return ModelResponse(parts=[ToolCallPart("pwd", {}, tool_call_id=str(requests))])

    with pytest.raises(ModelExecutionError, match="turn budget"):
        await _run(respond)
    assert requests == 4


async def test_read_focus_highlight_write_sequence_fits_the_request_limit():
    steps = [["read"], ["write"], ["focus", "highlight"]]
    executed = []
    executor = SimpleNamespace(
        execute=lambda name, args: executed.append(name) or {"ok": True},
        pending_canvas_edit_instruction=lambda: None,
    )

    def respond(messages, info):
        if steps:
            names = steps.pop(0)
            return ModelResponse(
                parts=[ToolCallPart(name, {}, tool_call_id=f"{name}-call") for name in names]
            )
        return _final()

    await native_tutor_turn(
        settings=SETTINGS,
        turn=_chat_turn("Add a note to the canvas."),
        messages=[{"role": "system", "content": "Tutor."}, {"role": "user", "content": "Hi"}],
        model=FunctionModel(respond),
        tool_executor=executor,
    )
    assert executed == ["read", "write", "focus", "highlight"]


async def test_each_turn_records_cached_input_tokens(caplog):
    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        await _run(lambda messages, info: _final())
    events = [json.loads(record.message) for record in caplog.records]
    usage = next(event for event in events if event["event"] == "tutor.turn_usage")
    assert usage["cached_input_tokens"] == 1_024
    assert usage["input_tokens"] == 1_200
    assert usage["stage"] == "chat"
    assert usage["requested_count"] == 1
