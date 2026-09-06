from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from contextvars import ContextVar
import os

import httpx
from openai import APIError, AsyncOpenAI
from pydantic_ai.exceptions import ModelAPIError
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIResponsesModel
from pydantic_ai.models.wrapper import WrapperModel
from pydantic_ai.providers.openai import OpenAIProvider

from lecturepilot.model_client import ModelExecutionError
from lecturepilot.model_provider_errors import model_provider_error_message
from lecturepilot.model_request_options import CANVAS_PLAN_REQUEST_TIMEOUT_SECONDS
from lecturepilot.model_usage import ModelUsageRecorder, complete_with_usage
from lecturepilot.models import ProviderSettings
from lecturepilot.providers import ProviderConfigurationError


class MeteredAuthoringModel(WrapperModel):
    """Keep application-wide provider quotas, retries and usage accounting."""

    def __init__(
        self, model, settings, recorder, authorize, response_usage=None, stage="canvas_authoring"
    ):
        super().__init__(model)
        self.provider_settings, self.recorder = settings, recorder
        self.authorize = authorize
        self.response_usage = response_usage
        self.stage = stage

    async def request(self, messages, model_settings, model_request_parameters):
        async def invoke(**kwargs):
            self.authorize()
            if self.response_usage is not None:
                self.response_usage.set(None)
            response = await self.wrapped.request(
                messages, model_settings, model_request_parameters
            )
            usage = response.usage
            if self.response_usage is not None:
                raw = self.response_usage.get()
                if raw is None:
                    raise ModelExecutionError("Provider response omitted usage accounting.")
                usage.input_tokens = raw.get("input_tokens", raw.get("prompt_tokens", 0))
                usage.output_tokens = raw.get("output_tokens", raw.get("completion_tokens", 0))
                usage.cache_read_tokens = (
                    raw.get("input_tokens_details", raw.get("prompt_tokens_details")) or {}
                ).get("cached_tokens", 0)
                usage.details["reasoning_tokens"] = (
                    raw.get("output_tokens_details", raw.get("completion_tokens_details")) or {}
                ).get("reasoning_tokens", 0)
            return {
                "response": response,
                "usage": {
                    "prompt_tokens": usage.input_tokens,
                    "completion_tokens": usage.output_tokens,
                    "prompt_tokens_details": {"cached_tokens": usage.cache_read_tokens},
                    "completion_tokens_details": {
                        "reasoning_tokens": usage.details.get("reasoning_tokens", 0)
                    },
                },
            }

        try:
            envelope = await complete_with_usage(
                self.recorder,
                invoke,
                usage_stage=self.stage,
                model=self.provider_settings.model,
                timeout=CANVAS_PLAN_REQUEST_TIMEOUT_SECONDS,
            )
        except (ModelAPIError, APIError, httpx.HTTPError, TimeoutError) as exc:
            raise ModelExecutionError(
                model_provider_error_message(
                    exc,
                    provider=self.provider_settings.provider,
                )
            ) from exc
        return envelope["response"]


@asynccontextmanager
async def authoring_model(
    settings: ProviderSettings,
    recorder: ModelUsageRecorder | None,
    authorize: Callable[[], None],
    *,
    stage: str = "canvas_authoring",
) -> AsyncIterator[MeteredAuthoringModel]:
    model_id = settings.model.partition("/")[2]
    api_key = os.environ.get(settings.api_key_env)
    if not api_key:
        raise ProviderConfigurationError(f"{settings.api_key_env} is required.")
    response_usage: ContextVar[dict | None] = ContextVar("authoring_provider_usage", default=None)

    async def observe_response(response: httpx.Response):
        from lecturepilot.model_rate_limits import observe_provider_response

        observe_provider_response(settings.model, response)
        if response.is_success:
            await response.aread()
            response_usage.set(response.json().get("usage"))

    if settings.provider in {"openai", "openrouter"}:
        base_url = (
            "https://openrouter.ai/api/v1"
            if settings.provider == "openrouter"
            else os.environ.get("OPENAI_BASE_URL")
        )
        async with httpx.AsyncClient(event_hooks={"response": [observe_response]}) as http_client:
            async with AsyncOpenAI(
                api_key=api_key, base_url=base_url, max_retries=0, http_client=http_client
            ) as client:
                model_type = (
                    OpenAIResponsesModel if settings.provider == "openai" else OpenAIChatModel
                )
                model = model_type(model_id, provider=OpenAIProvider(openai_client=client))
                yield MeteredAuthoringModel(
                    model, settings, recorder, authorize, response_usage, stage
                )
    elif settings.provider in {"google", "gemini"}:
        from google import genai
        from google.genai.types import HttpOptions, HttpRetryOptions
        from pydantic_ai.models.google import GoogleModel
        from pydantic_ai.providers.google import GoogleProvider

        client = genai.Client(
            api_key=api_key,
            http_options=HttpOptions(
                timeout=CANVAS_PLAN_REQUEST_TIMEOUT_SECONDS * 1000,
                retry_options=HttpRetryOptions(attempts=1),
            ),
        )
        try:
            model = GoogleModel(model_id, provider=GoogleProvider(client=client))
            yield MeteredAuthoringModel(model, settings, recorder, authorize, stage=stage)
        finally:
            await client.aio.aclose()
            client.close()
    else:
        raise ProviderConfigurationError("Unsupported authoring provider.")
