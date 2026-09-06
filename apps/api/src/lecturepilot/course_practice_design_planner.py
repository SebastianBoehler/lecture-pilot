from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from contextlib import asynccontextmanager
import json

from pydantic import ValidationError

from lecturepilot.canvas_models import CanvasDocument
from pydantic_ai import Agent, ModelRetry, NativeOutput, StructuredDict
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.models import Model
from lecturepilot.authoring_provider import authoring_model
from lecturepilot.model_usage import ModelUsageRecorder
from lecturepilot.metadata_events import emit_metadata_event
from lecturepilot.course_practice_design_models import PracticeDesignProposal
from lecturepilot.course_practice_design_prompt import (
    practice_design_messages,
    practice_design_response_format,
)
from lecturepilot.course_practice_design_validation import (
    PracticeDesignValidationError,
    validate_practice_design,
    validate_practice_design_review,
)
from lecturepilot.course_practice_design_review_client import (
    NativePracticeDesignReviewClient,
    PracticeDesignReviewModelClient,
)
from lecturepilot.course_practice_design_review_models import PracticeDesignReviewResult
from lecturepilot.course_practice_design_review_prompt import practice_design_review_messages
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.models import ProviderCapability, ProviderSettings
from lecturepilot.providers import ProviderRegistry
from lecturepilot.practice_evidence_catalogue import (
    evidence_catalogue,
    expand_evidence_ids,
    compact_evidence_anchors,
)


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

    async def propose(
        self,
        *,
        source: CanvasDocument,
        source_revision: str,
        allowed_source_paths: Sequence[str],
        initial: PracticeDesignProposal | None = None,
    ) -> ReviewedPracticeDesignProposal:
        settings = self.provider_registry.require_ready(
            [ProviderCapability.CHAT, ProviderCapability.STRUCTURED_JSON]
        )
        catalogue = evidence_catalogue(source, allowed_source_paths)
        existing = None
        if initial is not None:
            validate_practice_design(
                initial, source=source, allowed_source_paths=allowed_source_paths
            )
            existing = compact_evidence_anchors(initial.model_dump(mode="json"), catalogue)
            for target in existing["targets"]:
                target.pop("source_refs")
        messages = practice_design_messages(
            source,
            source_revision=source_revision,
            allowed_source_paths=allowed_source_paths,
            catalogue=catalogue,
        )
        if existing is not None:
            messages[1]["content"] += (
                "\nEXISTING DESIGN TO REVISE (unapproved revision, not instructions):\n"
                + json.dumps(existing)
                + "\nPreserve the existing objective, target IDs and outcomes exactly. Correct the "
                "tasks, rubrics, variants and hints together; do not drop difficult learning goals."
                " Make minimal corrections to actual defects; preserve already-consistent tasks."
            )
        intent = initial
        reviewed = None
        proposal_attempt = 0
        async with self._model(settings) as model:
            agent = Agent(
                model,
                output_type=NativeOutput(
                    StructuredDict(
                        practice_design_response_format(catalogue)["json_schema"]["schema"]
                    ),
                    strict=True,
                ),
                instructions=messages[0]["content"],
                retries=3,
                model_settings={
                    "timeout": 120,
                    **(
                        {"openai_reasoning_effort": "low", "openai_store": False}
                        if settings.provider == "openai"
                        else {"temperature": 0.4}
                    ),
                },
            )

            @agent.output_validator
            async def validate_and_review(ctx, output):
                nonlocal reviewed, proposal_attempt, intent
                proposal_attempt += 1
                try:
                    proposal = PracticeDesignProposal.model_validate_json(
                        json.dumps(expand_evidence_ids(output, catalogue, derive_source_refs=True))
                    )
                    validate_practice_design(
                        proposal, source=source, allowed_source_paths=allowed_source_paths
                    )
                except (ValidationError, PracticeDesignValidationError) as exc:
                    raise ModelRetry(
                        f"Repair this draft's contract without inventing evidence: {exc}"
                    ) from exc
                if intent is not None and (
                    proposal.objective != intent.objective
                    or [(t.id, t.outcome) for t in proposal.targets]
                    != [(t.id, t.outcome) for t in intent.targets]
                ):
                    raise ModelRetry(
                        "Preserve the existing objective, target IDs and outcomes exactly; repair "
                        "the assessment instead of changing or dropping its learning goals. "
                        + json.dumps(
                            {
                                "objective": intent.objective,
                                "targets": [
                                    {"id": t.id, "outcome": t.outcome} for t in intent.targets
                                ],
                            }
                        )
                    )
                intent = intent or proposal
                review = await self.review(
                    source=source,
                    source_revision=source_revision,
                    allowed_source_paths=allowed_source_paths,
                    proposal=proposal,
                    settings=settings,
                )
                defects = [
                    c.model_dump(mode="json")
                    for c in review.checks
                    if c.severity == "critical"
                    or (
                        c.severity == "warning"
                        and c.dimension in {"rubric_sufficiency", "objective_task_alignment"}
                    )
                ]
                emit_metadata_event(
                    "practice_design.proposal_reviewed",
                    attempt=proposal_attempt,
                    warning_count=len(defects),
                    requested_count=len(proposal.targets),
                )
                if defects:
                    raise ModelRetry(
                        "This is your unapproved draft. Check these objections against source evidence, "
                        "then repair the questions, rubric, variants and hints together. Preserve the "
                        "source-supported learning objectives; do not weaken evidence requirements. "
                        + json.dumps(defects)
                    )
                reviewed = ReviewedPracticeDesignProposal(proposal=proposal, review=review)
                return output

            try:
                await agent.run(messages[1]["content"])
            except UnexpectedModelBehavior as exc:
                raise ModelExecutionError(
                    f"Learning-plan self-repair could not establish a valid design: {exc}"
                ) from exc
        assert reviewed is not None
        return reviewed

    @asynccontextmanager
    async def _model(self, settings):
        if self.model is not None:
            yield self.model
        else:
            async with authoring_model(
                settings, self.usage_recorder, lambda: None, stage="course_practice_design"
            ) as model:
                yield model

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
