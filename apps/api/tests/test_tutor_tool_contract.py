import asyncio
import json
from types import SimpleNamespace
from threading import Event

import pytest

from lecturepilot.native_tutor import native_tutor_turn
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from lecturepilot.agent_turn_orchestration import _run_agent_harness
from lecturepilot.models import ProviderSettings
from lecturepilot.observability import Observability
from test_strict_model_payload import _payload, _turn


async def _complete(completion, executor):
    return await native_tutor_turn(
        model=FunctionModel(completion),
        settings=ProviderSettings(
            provider="openai", model="openai/test", api_key_env="OPENAI_API_KEY", capabilities=set()
        ),
        turn=_turn(),
        tool_executor=executor,
        observability=Observability(),
        emit=None,
        messages=[{"role": "system", "content": "Tutor."}, {"role": "user", "content": "Answer"}],
    )


def _response(*, calls=None):
    return ModelResponse(parts=calls or [TextPart(json.dumps(_payload()))])


async def test_slow_tool_does_not_block_other_event_loop_work():
    entered, release = Event(), Event()
    calls = 0

    def execute(name, args):
        entered.set()
        if not release.wait(1):
            raise RuntimeError("Event loop blocked behind synchronous tool")
        return {"ok": True}

    async def completion(messages, info):
        nonlocal calls
        calls += 1
        return (
            _response(calls=[ToolCallPart("pwd", {}, tool_call_id="slow")])
            if calls == 1
            else _response()
        )

    task = asyncio.create_task(
        _complete(
            completion,
            SimpleNamespace(execute=execute, pending_canvas_edit_instruction=lambda: None),
        )
    )
    try:
        for _ in range(200):
            if entered.is_set():
                break
            await asyncio.sleep(0.005)
        assert entered.is_set()
        release.set()
        await task
    finally:
        release.set()
        if not task.done():
            await task


async def test_harness_type_error_is_not_retried_after_side_effects():
    calls = 0

    class Harness:
        async def run_turn(self, turn, **kwargs):
            nonlocal calls
            calls += 1
            if kwargs:
                raise TypeError("nested call got an unexpected keyword argument 'option'")
            return object()

    with pytest.raises(TypeError, match="unexpected keyword"):
        await _run_agent_harness(
            Harness(),
            turn=_turn(),
            tool_executor=None,
            observability=Observability(),
            emit=lambda _: None,
        )
    assert calls == 1
