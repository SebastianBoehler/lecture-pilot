import asyncio
from threading import Event

import pytest

from lecturepilot.model_usage import _scope, complete_with_usage, model_usage_scope


@pytest.mark.parametrize("failed", [False, True])
async def test_slow_usage_recorder_preserves_scope_without_blocking_event_loop(failed):
    loop = asyncio.get_running_loop()
    started, release = asyncio.Event(), Event()
    recorded = []

    class Recorder:
        def record_response(self, response, **kwargs):
            self.record_failure(**kwargs)

        def record_failure(self, **kwargs):
            loop.call_soon_threadsafe(started.set)
            responsive = release.wait(2)
            recorded.append((_scope.get(), responsive))

    async def completion(**kwargs):
        if failed:
            raise ValueError("provider rejected request")
        return {"usage": {"prompt_tokens": 2, "completion_tokens": 1}}

    async def heartbeat():
        await started.wait()
        release.set()

    with model_usage_scope(actor_user_id="actor", course_id="course", workload="tutor"):
        pulse = asyncio.create_task(heartbeat())
        try:
            if failed:
                with pytest.raises(ValueError, match="provider rejected"):
                    await complete_with_usage(Recorder(), completion, model="openai/test")
            else:
                await complete_with_usage(Recorder(), completion, model="openai/test")
        finally:
            release.set()
            await pulse
    scope, responsive = recorded[0]
    assert responsive, "Usage recording blocked the event loop."
    assert scope.actor_user_id == "actor"
    assert scope.course_id == "course"
    assert scope.workload == "tutor"


async def test_recorder_error_does_not_repeat_paid_response():
    calls = 0

    class Recorder:
        def record_response(self, response, **kwargs):
            raise TimeoutError("recording failed")

    async def completion(**kwargs):
        nonlocal calls
        calls += 1
        return {"usage": {"prompt_tokens": 2, "completion_tokens": 1}}

    with pytest.raises(TimeoutError, match="recording failed"):
        await complete_with_usage(Recorder(), completion, model="openai/test")
    assert calls == 1
