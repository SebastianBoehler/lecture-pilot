from __future__ import annotations

from typing import Protocol
from collections.abc import Sequence

from lecturepilot.course_canvas_json import parse_model_json
from lecturepilot.course_practice_design_review_prompt import (
    practice_design_review_response_format,
)
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.model_provider_errors import model_provider_error_message
from lecturepilot.model_request_options import completion_options
from lecturepilot.model_usage import ModelUsageRecorder, complete_with_usage
from lecturepilot.models import ProviderSettings
from lecturepilot.providers import ProviderConfigurationError
from lecturepilot.practice_evidence_catalogue import EvidenceCatalogue, expand_evidence_ids


class PracticeDesignReviewModelClient(Protocol):
    async def complete_review(
        self,
        *,
        settings: ProviderSettings,
        messages: list[dict[str, str]],
        allowed_source_paths: Sequence[str],
        catalogue: EvidenceCatalogue,
    ) -> dict:
        """Return one strict semantic review payload."""


class LiteLLMPracticeDesignReviewClient:
    def __init__(self, usage_recorder: ModelUsageRecorder | None = None) -> None:
        self.usage_recorder = usage_recorder

    async def complete_review(
        self,
        *,
        settings: ProviderSettings,
        messages: list[dict[str, str]],
        allowed_source_paths: Sequence[str],
        catalogue: EvidenceCatalogue,
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
                usage_stage="course_practice_design_review",
                model=settings.model,
                messages=messages,
                response_format=practice_design_review_response_format(catalogue),
                **completion_options(settings, temperature=0.0, reasoning_effort="low"),
            )
        except ProviderConfigurationError:
            raise
        except Exception as exc:
            raise ModelExecutionError(
                model_provider_error_message(exc, provider=settings.provider)
            ) from exc
        return expand_evidence_ids(parse_model_json(response.choices[0].message.content), catalogue)
