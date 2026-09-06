from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from pydantic import ValidationError

from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.course_practice_design_client import (
    LiteLLMPracticeDesignClient,
    PracticeDesignModelClient,
)
from lecturepilot.course_practice_design_models import PracticeDesignProposal
from lecturepilot.course_practice_design_prompt import practice_design_messages
from lecturepilot.course_practice_design_validation import (
    PracticeDesignValidationError,
    validate_practice_design,
    validate_practice_design_review,
)
from lecturepilot.course_practice_design_review_client import (
    LiteLLMPracticeDesignReviewClient,
    PracticeDesignReviewModelClient,
)
from lecturepilot.course_practice_design_review_models import PracticeDesignReviewResult
from lecturepilot.course_practice_design_review_prompt import practice_design_review_messages
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.models import ProviderCapability, ProviderSettings
from lecturepilot.providers import ProviderRegistry
from lecturepilot.practice_evidence_catalogue import evidence_catalogue


@dataclass(frozen=True)
class ReviewedPracticeDesignProposal:
    proposal: PracticeDesignProposal
    review: PracticeDesignReviewResult


class PracticeDesignPlanner:
    def __init__(
        self,
        provider_registry: ProviderRegistry | None = None,
        model_client: PracticeDesignModelClient | None = None,
        review_client: PracticeDesignReviewModelClient | None = None,
    ) -> None:
        self.provider_registry = provider_registry or ProviderRegistry.from_env()
        self.model_client = model_client or LiteLLMPracticeDesignClient()
        self.review_client = review_client or LiteLLMPracticeDesignReviewClient()

    async def propose(
        self,
        *,
        source: CanvasDocument,
        source_revision: str,
        allowed_source_paths: Sequence[str],
    ) -> ReviewedPracticeDesignProposal:
        settings = self.provider_registry.require_ready(
            [ProviderCapability.CHAT, ProviderCapability.STRUCTURED_JSON]
        )
        try:
            proposal = PracticeDesignProposal.model_validate(
                await self.model_client.complete_proposal(
                    settings=settings,
                    catalogue=evidence_catalogue(source, allowed_source_paths),
                    messages=practice_design_messages(
                        source,
                        source_revision=source_revision,
                        allowed_source_paths=allowed_source_paths,
                    ),
                )
            )
            validate_practice_design(
                proposal,
                source=source,
                allowed_source_paths=allowed_source_paths,
            )
        except (ValidationError, PracticeDesignValidationError) as exc:
            raise ModelExecutionError(
                f"Practice-design proposal violated its contract: {exc}"
            ) from exc
        review = await self.review(
            source=source,
            source_revision=source_revision,
            allowed_source_paths=allowed_source_paths,
            proposal=proposal,
            settings=settings,
        )
        return ReviewedPracticeDesignProposal(proposal=proposal, review=review)

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
        except (ValidationError, PracticeDesignValidationError) as exc:
            raise ModelExecutionError(
                f"Practice-design semantic review violated its contract: {exc}"
            ) from exc
        return review
