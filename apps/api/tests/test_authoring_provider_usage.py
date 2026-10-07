from contextvars import ContextVar

from pydantic_ai import Agent
from pydantic_ai.messages import ModelResponse, TextPart
from pydantic_ai.models.function import FunctionModel
import pytest

from lecturepilot.authoring_provider import MeteredAuthoringModel
from lecturepilot.model_client import ModelExecutionError
from test_authoring_job import authoring_job


@pytest.mark.parametrize(
    "raw",
    [
        {
            "input_tokens": 100,
            "output_tokens": 20,
            "input_tokens_details": {"cached_tokens": 60},
            "output_tokens_details": {"reasoning_tokens": 5},
        },
        {
            "prompt_tokens": 100,
            "completion_tokens": 20,
            "prompt_tokens_details": {"cached_tokens": 60},
            "completion_tokens_details": {"reasoning_tokens": 5},
        },
        {
            "prompt_tokens": 100,
            "completion_tokens": 20,
            "prompt_tokens_details": None,
            "completion_tokens_details": None,
        },
    ],
)
async def test_raw_usage_survives_unknown_model_price_catalogue(tmp_path, raw):
    job = authoring_job(tmp_path)
    response_usage = ContextVar("test_provider_usage", default=None)

    async def respond(messages, info):
        response_usage.set(raw)
        return ModelResponse(parts=[TextPart("Done")])

    model = MeteredAuthoringModel(
        FunctionModel(respond), job.settings, None, job.authorize, response_usage
    )
    result = await Agent(model).run("Report usage")
    assert result.usage.input_tokens == 100
    assert result.usage.output_tokens == 20
    nullable_details = raw.get("prompt_tokens_details", {}) is None
    assert result.usage.cache_read_tokens == (0 if nullable_details else 60)
    assert result.usage.details["reasoning_tokens"] == (0 if nullable_details else 5)


async def test_missing_usage_cannot_reuse_previous_response_usage(tmp_path):
    job = authoring_job(tmp_path)
    response_usage = ContextVar("test_stale_usage", default={"input_tokens": 999})
    model = MeteredAuthoringModel(
        FunctionModel(lambda messages, info: ModelResponse(parts=[TextPart("Done")])),
        job.settings,
        None,
        job.authorize,
        response_usage,
    )
    with pytest.raises(ModelExecutionError, match="omitted usage"):
        await Agent(model).run("Report usage")


async def test_nested_critics_share_provider_client_and_keep_stage(tmp_path):
    from lecturepilot.authoring_provider import _pooled_model, authoring_model

    job = authoring_job(tmp_path)
    model = FunctionModel(lambda messages, info: ModelResponse(parts=[TextPart("Done")]))
    async with _pooled_model(model, job.settings, None, job.authorize, None, "author") as author:
        async with authoring_model(job.settings, None, job.authorize, stage="critic") as critic:
            assert critic.wrapped is author.wrapped
            assert critic.stage == "critic"
            assert author.stage == "author"


async def test_successful_over_budget_response_still_records_paid_usage(tmp_path):
    from lecturepilot.authoring_limits import authoring_budget, AuthoringBudgetExceeded
    from lecturepilot.model_usage_total import model_usage_total

    job = authoring_job(tmp_path)
    raw_usage = ContextVar("paid_usage", default=None)

    async def respond(messages, info):
        raw_usage.set({"input_tokens": 100, "output_tokens": 20})
        return ModelResponse(parts=[TextPart("Done")])

    model = MeteredAuthoringModel(
        FunctionModel(respond), job.settings, None, job.authorize, raw_usage
    )
    with model_usage_total() as total, authoring_budget(input_tokens_limit=1):
        with pytest.raises(AuthoringBudgetExceeded, match="token"):
            await Agent(model).run("Report usage")
        assert total.total_tokens == 120


@pytest.mark.parametrize(
    "raw",
    [
        None,
        {},
        {"input_tokens": 1},
        {"input_tokens": -1, "output_tokens": 2},
        {"prompt_tokens": True, "completion_tokens": 2},
        {"prompt_tokens": 1, "completion_tokens": "2"},
    ],
)
async def test_invalid_native_usage_retains_unknown_paid_cost(tmp_path, raw):
    from lecturepilot.model_usage_total import model_usage_total

    job = authoring_job(tmp_path)
    response_usage = ContextVar("invalid_provider_usage", default=None)

    async def respond(messages, info):
        response_usage.set(raw)
        return ModelResponse(parts=[TextPart("Done")])

    model = MeteredAuthoringModel(
        FunctionModel(respond), job.settings, None, job.authorize, response_usage
    )
    with model_usage_total() as total:
        with pytest.raises(ModelExecutionError, match="usage accounting"):
            await Agent(model).run("Report usage")
        assert total.total_tokens is None


async def test_explicit_zero_native_usage_is_valid(tmp_path):
    from lecturepilot.model_usage_total import model_usage_total

    job = authoring_job(tmp_path)
    response_usage = ContextVar("zero_provider_usage", default=None)

    async def respond(messages, info):
        response_usage.set({"input_tokens": 0, "output_tokens": 0})
        return ModelResponse(parts=[TextPart("Done")])

    model = MeteredAuthoringModel(
        FunctionModel(respond), job.settings, None, job.authorize, response_usage
    )
    with model_usage_total() as total:
        result = await Agent(model).run("Report usage")
        assert result.usage.input_tokens == result.usage.output_tokens == 0
        assert total.total_tokens == 0
