import asyncio

import pytest
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel

from lecturepilot.authoring_job import run_authoring_job
from lecturepilot.authoring_limits import AuthoringBudgetExceeded, authoring_budget
from lecturepilot.authoring_provider import MeteredAuthoringModel
from lecturepilot.authoring_state import load_state
from test_authoring_job import authoring_job


async def test_request_budget_covers_nested_metered_calls(tmp_path):
    job = authoring_job(tmp_path)
    calls = 0

    def respond(messages, info):
        nonlocal calls
        calls += 1
        return ModelResponse(parts=[ToolCallPart("read", {"path": "/evidence/topic.md"})])

    model = MeteredAuthoringModel(FunctionModel(respond), job.settings, None, job.authorize)
    with authoring_budget(request_limit=2, input_tokens_limit=100_000, output_tokens_limit=100_000):
        with pytest.raises(AuthoringBudgetExceeded, match="request"):
            await run_authoring_job(job, model=model)
    assert calls == 2
    assert not load_state(job).completed


async def test_authoring_deadline_cancels_provider_and_keeps_previous_checkpoint(
    tmp_path, monkeypatch
):
    import lecturepilot.authoring_job as module

    job = authoring_job(tmp_path)
    calls = 0

    async def respond(messages, info):
        nonlocal calls
        calls += 1
        if calls == 1:
            return ModelResponse(parts=[ToolCallPart("read", {"path": "/evidence/topic.md"})])
        await asyncio.Event().wait()

    monkeypatch.setattr(module, "AUTHORING_DEADLINE_SECONDS", 0.03)
    with pytest.raises(AuthoringBudgetExceeded, match="deadline"):
        await run_authoring_job(job, model=FunctionModel(respond))
    state = load_state(job)
    assert state.metrics.model_requests == 1
    assert not state.completed
