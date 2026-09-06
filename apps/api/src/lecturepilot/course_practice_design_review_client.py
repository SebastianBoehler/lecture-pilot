from __future__ import annotations

from typing import Protocol
from collections.abc import Sequence
from contextlib import asynccontextmanager
import json
from pydantic import ValidationError
from pydantic_ai import Agent, ModelRetry, NativeOutput, StructuredDict
from pydantic_ai.exceptions import UnexpectedModelBehavior

from lecturepilot.authoring_provider import authoring_model
from lecturepilot.course_practice_design_review_prompt import (
    practice_design_review_response_format,
)
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.model_usage import ModelUsageRecorder
from lecturepilot.models import ProviderSettings
from lecturepilot.course_practice_design_review_models import PracticeDesignReviewResult
from lecturepilot.course_practice_design_validation import PracticeDesignValidationError
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


class NativePracticeDesignReviewClient:
    def __init__(self, usage_recorder: ModelUsageRecorder | None = None, *, model=None) -> None:
        self.usage_recorder = usage_recorder
        self.model = model

    async def complete_review(
        self,
        *,
        settings: ProviderSettings,
        messages: list[dict[str, str]],
        allowed_source_paths: Sequence[str],
        catalogue: EvidenceCatalogue,
    ) -> dict:
        schema = practice_design_review_response_format(catalogue)["json_schema"]["schema"]
        async with self._model(settings) as model:
            agent = Agent(
                model,
                output_type=NativeOutput(StructuredDict(schema), strict=True),
                retries=2,
                instructions=messages[0]["content"],
                model_settings={
                    "timeout": 120,
                    **(
                        {"openai_reasoning_effort": "medium", "openai_store": False}
                        if settings.provider == "openai"
                        else {"temperature": 0.0}
                    ),
                },
            )

            @agent.output_validator
            def require_valid_review(ctx, output):
                try:
                    review = PracticeDesignReviewResult.model_validate_json(
                        json.dumps(expand_evidence_ids(output, catalogue))
                    )
                except (ValidationError, PracticeDesignValidationError) as exc:
                    raise ModelRetry(
                        f"Correct your review's structure and source support: {exc}"
                    ) from exc
                return review.model_dump(mode="json")

            try:
                return (await agent.run(messages[1]["content"])).output
            except UnexpectedModelBehavior as exc:
                raise ModelExecutionError(
                    f"Practice-design reviewer could not produce valid evidence-backed feedback: {exc}"
                ) from exc

    @asynccontextmanager
    async def _model(self, settings):
        if self.model is not None:
            yield self.model
        else:
            async with authoring_model(
                settings, self.usage_recorder, lambda: None, stage="course_practice_design_review"
            ) as model:
                yield model
