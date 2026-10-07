"""One-shot structured requests through the shared metered native gateway."""

from contextlib import asynccontextmanager
from collections.abc import Callable
import httpx
from openai import APIError

from pydantic_ai import Agent, ModelRetry, NativeOutput, StructuredDict
from pydantic_ai.exceptions import UnexpectedModelBehavior, ModelAPIError

from lecturepilot.authoring_provider import authoring_model
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.model_provider_errors import model_provider_error_message
from lecturepilot.providers import ProviderConfigurationError, workload_settings
from lecturepilot.native_model_settings import native_model_settings


async def native_completion(
    *,
    settings,
    messages,
    response_format,
    stage,
    recorder=None,
    model=None,
    temperature=0.0,
    reasoning_effort="low",
    max_tokens=16_000,
    validate: Callable | None = None,
    tier=None,
):
    if tier is not None:
        settings = workload_settings(settings, tier)
    schema = response_format["json_schema"]["schema"]
    instructions = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
    prompt = "\n\n".join(m["content"] for m in messages if m["role"] != "system")

    @asynccontextmanager
    async def provider():
        if model is not None:
            yield model
        else:
            async with authoring_model(settings, recorder, lambda: None, stage=stage) as gateway:
                yield gateway

    async with provider() as gateway:
        agent = Agent(
            gateway,
            output_type=NativeOutput(StructuredDict(schema), strict=True),
            instructions=instructions,
            retries=2,
            model_settings=native_model_settings(
                settings,
                temperature=temperature,
                reasoning_effort=reasoning_effort,
                max_tokens=max_tokens,
            ),
        )
        if validate is not None:

            @agent.output_validator
            def validate_output(ctx, output):
                try:
                    return validate(output)
                except (ValueError, ModelExecutionError) as exc:
                    raise ModelRetry(str(exc)) from exc

        try:
            return (await agent.run(prompt)).output
        except UnexpectedModelBehavior as exc:
            raise ModelExecutionError(f"{stage} returned invalid structured output: {exc}") from exc
        except (ModelExecutionError, ProviderConfigurationError):
            raise
        except Exception as exc:
            if isinstance(exc, (APIError, ModelAPIError, httpx.HTTPError, TimeoutError)) or (
                isinstance(getattr(exc, "status_code", None), int) and exc.status_code >= 400
            ):
                raise ModelExecutionError(
                    model_provider_error_message(exc, provider=settings.provider)
                ) from exc
            raise
