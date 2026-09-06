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
    assert result.usage.cache_read_tokens == 60
    assert result.usage.details["reasoning_tokens"] == 5


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
