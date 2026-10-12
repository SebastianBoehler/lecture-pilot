from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from contextlib import asynccontextmanager

from pydantic import ValidationError

from lecturepilot.canvas.canvas_models import CanvasDocument
from pydantic_ai.models import Model
from lecturepilot.authoring.authoring_provider import authoring_model
from lecturepilot.llm.model_usage import ModelUsageRecorder
from lecturepilot.learning_design.course_practice_design_models import PracticeDesignProposal
from lecturepilot.learning_design.course_practice_design_validation import (
    validate_practice_design,
    validate_practice_design_review,
)
from lecturepilot.learning_design.course_practice_design_review_client import (
    NativePracticeDesignReviewClient,
    PracticeDesignReviewModelClient,
)
from lecturepilot.learning_design.course_practice_design_review_models import (
    PracticeDesignReviewResult,
)
from lecturepilot.learning_design.course_practice_design_review_prompt import (
    practice_design_review_messages,
)
from lecturepilot.llm.model_client import ModelExecutionError
from lecturepilot.core.models import ProviderCapability, ProviderSettings
from lecturepilot.llm.providers import ProviderRegistry
from lecturepilot.llm.model_job_limits import bounded_model_job
from lecturepilot.learning_design.practice_evidence_catalogue import evidence_catalogue


@dataclass(frozen=True)
class ReviewedPracticeDesignProposal:
    proposal: PracticeDesignProposal
    review: PracticeDesignReviewResult


class PracticeDesignPlanner:
    def __init__(
        self,
        provider_registry: ProviderRegistry | None = None,
        model: Model | None = None,
        usage_recorder: ModelUsageRecorder | None = None,
        review_client: PracticeDesignReviewModelClient | None = None,
    ) -> None:
        self.provider_registry = provider_registry or ProviderRegistry.from_env()
        self.model = model
        self.usage_recorder = usage_recorder
        self.review_client = review_client or NativePracticeDesignReviewClient(usage_recorder)

    @asynccontextmanager
    async def _model(self, settings, *, stage="course_practice_design", authorize=None):
        if self.model is not None:
            yield self.model
        else:
            async with authoring_model(
                settings, self.usage_recorder, authorize or (lambda: None), stage=stage
            ) as model:
                yield model

    @bounded_model_job
    async def review(
        self,
        *,
        source: CanvasDocument,
        source_revision: str,
        allowed_source_paths: Sequence[str],
        proposal: PracticeDesignProposal,
        settings: ProviderSettings | None = None,
    ) -> PracticeDesignReviewResult:
        settings = settings or self.provider_registry.require_ready(
            [ProviderCapability.CHAT, ProviderCapability.STRUCTURED_JSON]
        )
        try:
            validate_practice_design(
                proposal,
                source=source,
                allowed_source_paths=allowed_source_paths,
            )
            catalogue = evidence_catalogue(source, allowed_source_paths)
            messages = practice_design_review_messages(
                source,
                proposal,
                source_revision=source_revision,
                allowed_source_paths=allowed_source_paths,
                catalogue=catalogue,
            )
            review = PracticeDesignReviewResult.model_validate(
                await self.review_client.complete_review(
                    settings=settings,
                    source=source,
                    proposal=proposal,
                    allowed_source_paths=allowed_source_paths,
                    messages=messages,
                    catalogue=catalogue,
                )
            )
            validate_practice_design_review(
                review,
                proposal,
                source=source,
                allowed_source_paths=allowed_source_paths,
            )
        except (ValidationError, ValueError) as exc:
            raise ModelExecutionError(
                f"Practice-design semantic review violated its contract: {exc}"
            ) from exc
        return review
