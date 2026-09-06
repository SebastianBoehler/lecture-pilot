from __future__ import annotations

from typing import Protocol

from lecturepilot.course_canvas_json import parse_model_json
from lecturepilot.course_practice_design_prompt import practice_design_response_format
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.model_provider_errors import model_provider_error_message
from lecturepilot.model_request_options import completion_options
from lecturepilot.model_usage import ModelUsageRecorder, complete_with_usage
from lecturepilot.models import ProviderSettings
from lecturepilot.providers import ProviderConfigurationError
from lecturepilot.practice_evidence_catalogue import EvidenceCatalogue, expand_evidence_ids


class PracticeDesignModelClient(Protocol):
    async def complete_proposal(
        self,
        *,
        settings: ProviderSettings,
        messages: list[dict[str, str]],
        catalogue: EvidenceCatalogue,
    ) -> dict:
        """Return one structured practice-design proposal."""


class LiteLLMPracticeDesignClient:
    def __init__(self, usage_recorder: ModelUsageRecorder | None = None) -> None:
        self.usage_recorder = usage_recorder

    async def complete_proposal(
        self,
        *,
        settings: ProviderSettings,
        messages: list[dict[str, str]],
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
                usage_stage="course_practice_design",
                model=settings.model,
                messages=messages,
                response_format=practice_design_response_format(catalogue),
                **completion_options(settings, temperature=0.4, max_tokens=6000),
            )
        except ProviderConfigurationError:
            raise
        except Exception as exc:
            raise ModelExecutionError(
                model_provider_error_message(exc, provider=settings.provider)
            ) from exc
        return expand_evidence_ids(
            parse_model_json(response.choices[0].message.content),
            catalogue,
            derive_source_refs=True,
        )
