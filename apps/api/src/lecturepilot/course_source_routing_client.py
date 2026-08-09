from __future__ import annotations

from typing import Protocol

from lecturepilot.agent_response_schema import (
    source_routing_response_format,
    source_routing_review_response_format,
)
from lecturepilot.course_canvas_json import parse_model_json
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.model_request_options import completion_options
from lecturepilot.model_usage import ModelUsageRecorder, complete_with_usage
from lecturepilot.models import ProviderSettings
from lecturepilot.providers import ProviderConfigurationError


class SourceRoutingModelClient(Protocol):
    async def complete_routing(
        self, *, settings: ProviderSettings, messages: list[dict[str, str]]
    ) -> dict:
        """Return one validated source assignment per listed file."""

    async def review_routing(
        self, *, settings: ProviderSettings, messages: list[dict[str, str]]
    ) -> dict:
        """Return corrections after reviewing the complete proposed manifest."""


class LiteLLMSourceRoutingClient:
    def __init__(self, usage_recorder: ModelUsageRecorder | None = None) -> None:
        self.usage_recorder = usage_recorder

    async def complete_routing(
        self, *, settings: ProviderSettings, messages: list[dict[str, str]]
    ) -> dict:
        return await self._complete(
            settings=settings,
            messages=messages,
            response_format=source_routing_response_format(),
        )

    async def review_routing(
        self, *, settings: ProviderSettings, messages: list[dict[str, str]]
    ) -> dict:
        return await self._complete(
            settings=settings,
            messages=messages,
            response_format=source_routing_review_response_format(),
        )

    async def _complete(
        self,
        *,
        settings: ProviderSettings,
        messages: list[dict[str, str]],
        response_format: dict,
    ) -> dict:
        try:
            from litellm import acompletion
        except ImportError as exc:
            raise ProviderConfigurationError(
                'litellm is not installed. Install the backend with the "agent" extra.'
            ) from exc
        try:
            response = await complete_with_usage(
                self.usage_recorder,
                acompletion,
                model=settings.model,
                messages=messages,
                response_format=response_format,
                **completion_options(settings, temperature=0.1, max_tokens=8000),
            )
        except Exception as exc:
            raise ModelExecutionError("Source-routing model request failed.") from exc
        return parse_model_json(response.choices[0].message.content)
