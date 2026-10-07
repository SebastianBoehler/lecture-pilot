from __future__ import annotations

from typing import Protocol

from lecturepilot.agent_response_schema import (
    source_routing_response_format,
    source_routing_review_response_format,
)
from lecturepilot.native_completion import native_completion
from lecturepilot.model_usage import ModelUsageRecorder
from lecturepilot.models import ProviderSettings


class SourceRoutingModelClient(Protocol):
    async def complete_routing(
        self, *, settings: ProviderSettings, messages: list[dict[str, str]]
    ) -> dict:
        """Return selected non-primary sources for the complete inventory."""

    async def review_routing(
        self, *, settings: ProviderSettings, messages: list[dict[str, str]]
    ) -> dict:
        """Return corrections after reviewing the complete proposed manifest."""


class NativeSourceRoutingClient:
    def __init__(self, usage_recorder: ModelUsageRecorder | None = None, *, model=None) -> None:
        self.usage_recorder, self.model = usage_recorder, model

    async def complete_routing(
        self, *, settings: ProviderSettings, messages: list[dict[str, str]]
    ) -> dict:
        return await self._complete(
            settings=settings,
            messages=messages,
            response_format=source_routing_response_format(),
            tier="utility",
        )

    async def review_routing(
        self, *, settings: ProviderSettings, messages: list[dict[str, str]]
    ) -> dict:
        return await self._complete(
            settings=settings,
            messages=messages,
            response_format=source_routing_review_response_format(),
            tier="critic",
        )

    async def _complete(
        self,
        *,
        settings: ProviderSettings,
        messages: list[dict[str, str]],
        response_format: dict,
        tier: str,
    ) -> dict:
        return await native_completion(
            settings=settings,
            messages=messages,
            response_format=response_format,
            stage="course_source_routing",
            tier=tier,
            recorder=self.usage_recorder,
            model=self.model,
            temperature=0.4,
            max_tokens=8000,
        )
