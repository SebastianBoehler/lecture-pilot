import asyncio

import pytest
from pydantic_ai.models.function import FunctionModel

from lecturepilot.authoring_limits import (
    AuthoringBudgetExceeded,
    authoring_budget,
    current_authoring_budget,
)
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.models import ProviderCapability
from lecturepilot.model_job_limits import bounded_model_job
from lecturepilot.native_completion import native_completion
from practice_exam_planner_fixtures import _Registry


@pytest.mark.parametrize("error", [ValueError("internal bug"), KeyError("internal field")])
async def test_native_completion_preserves_programming_errors(error):
    def fail(messages, info):
        raise error

    with pytest.raises(type(error), match="internal"):
        await complete(FunctionModel(fail))


async def test_native_completion_maps_explicit_provider_http_errors():
    class CreditsError(Exception):
        status_code = 402

    def fail(messages, info):
        raise CreditsError("Insufficient credits")

    with pytest.raises(ModelExecutionError, match="credits"):
        await complete(FunctionModel(fail))


async def complete(model):
    return await native_completion(
        settings=_Registry().require_ready(
            [ProviderCapability.CHAT, ProviderCapability.STRUCTURED_JSON]
        ),
        messages=[{"role": "user", "content": "Return the result."}],
        response_format={
            "json_schema": {
                "schema": {
                    "type": "object",
                    "properties": {"ok": {"type": "boolean"}},
                    "required": ["ok"],
                    "additionalProperties": False,
                }
            }
        },
        stage="test",
        model=model,
    )


async def test_planning_job_and_nested_reviewer_share_the_same_request_budget():
    observed = []

    @bounded_model_job
    async def reviewer():
        observed.append(current_authoring_budget())
        current_authoring_budget().reserve_request()

    @bounded_model_job
    async def proposal():
        current_authoring_budget().reserve_request()
        await reviewer()

    with authoring_budget(request_limit=1) as budget:
        with pytest.raises(AuthoringBudgetExceeded, match="request budget"):
            await proposal()
        assert observed == [budget]
    assert current_authoring_budget() is None


async def test_planning_job_cancels_work_at_its_deadline(monkeypatch):
    monkeypatch.setattr("lecturepilot.model_job_limits.AUTHORING_DEADLINE_SECONDS", 0.01)
    cancelled = asyncio.Event()

    @bounded_model_job
    async def proposal():
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    with pytest.raises(AuthoringBudgetExceeded, match="deadline"):
        await proposal()
    assert cancelled.is_set()
    assert current_authoring_budget() is None
