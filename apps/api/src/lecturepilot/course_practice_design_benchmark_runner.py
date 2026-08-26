from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import Any, Protocol

from lecturepilot.course_practice_design_benchmark_evaluator import (
    LiteLLMPracticeDesignBenchmarkClient,
    PracticeDesignBenchmarkModelClient,
    practice_design_benchmark_messages,
    validate_practice_design_benchmark_evaluation,
)
from lecturepilot.course_practice_design_benchmark_fixtures import (
    PracticeDesignBenchmarkFixture,
)
from lecturepilot.course_practice_design_benchmark_models import (
    PracticeDesignBenchmarkReviewerJudgment,
    summarize_dimension_scores,
)
from lecturepilot.course_practice_design_benchmark_report import (
    PracticeDesignBenchmarkError,
    PracticeDesignBenchmarkFixtureResult,
    PracticeDesignBenchmarkReport,
    PracticeDesignBenchmarkReviewerResult,
)
from lecturepilot.course_practice_design_models import PracticeDesignProposal
from lecturepilot.course_practice_design_planner import (
    PracticeDesignPlanner,
    ReviewedPracticeDesignProposal,
)
from lecturepilot.course_practice_design_review_models import PracticeDesignReviewResult
from lecturepilot.course_practice_design_validation import (
    validate_practice_design,
    validate_practice_design_review,
)
from lecturepilot.models import ProviderCapability
from lecturepilot.providers import ProviderRegistry


class PracticeDesignBenchmarkPlanner(Protocol):
    async def propose(
        self,
        *,
        source: Any,
        source_revision: str,
        allowed_source_paths: Sequence[str],
    ) -> ReviewedPracticeDesignProposal:
        """Return the validated production proposal and semantic review."""


async def run_practice_design_benchmark(
    *,
    fixtures: Sequence[PracticeDesignBenchmarkFixture],
    proposal_model: str,
    reviewer_models: Sequence[str],
    planner: PracticeDesignBenchmarkPlanner | None = None,
    evaluation_client: PracticeDesignBenchmarkModelClient | None = None,
    registry_factory: Callable[[str], Any] = ProviderRegistry.from_env,
    generated_at: datetime | None = None,
) -> PracticeDesignBenchmarkReport:
    reviewer_models = tuple(reviewer_models)
    if len(reviewer_models) < 2 or len(set(reviewer_models)) != len(reviewer_models):
        raise ValueError("Provide at least two distinct reviewer models.")
    production_planner = planner or PracticeDesignPlanner(
        provider_registry=ProviderRegistry.from_env(proposal_model)
    )
    client = evaluation_client or LiteLLMPracticeDesignBenchmarkClient()
    results = []
    for fixture in fixtures:
        results.append(
            await _run_fixture(
                fixture,
                proposal_model=proposal_model,
                reviewer_models=reviewer_models,
                planner=production_planner,
                evaluation_client=client,
                registry_factory=registry_factory,
            )
        )
    return PracticeDesignBenchmarkReport(
        generated_at=generated_at or datetime.now(UTC),
        proposal_model=proposal_model,
        reviewer_models=reviewer_models,
        fixtures=tuple(results),
    )


async def _run_fixture(
    fixture: PracticeDesignBenchmarkFixture,
    *,
    proposal_model: str,
    reviewer_models: tuple[str, ...],
    planner: PracticeDesignBenchmarkPlanner,
    evaluation_client: PracticeDesignBenchmarkModelClient,
    registry_factory: Callable[[str], Any],
) -> PracticeDesignBenchmarkFixtureResult:
    try:
        reviewed = await planner.propose(
            source=fixture.source,
            source_revision=fixture.source_revision,
            allowed_source_paths=fixture.allowed_source_paths,
        )
        proposal = PracticeDesignProposal.model_validate(reviewed.proposal)
        production_review = PracticeDesignReviewResult.model_validate(reviewed.review)
        validate_practice_design(
            proposal,
            source=fixture.source,
            allowed_source_paths=fixture.allowed_source_paths,
        )
        validate_practice_design_review(
            production_review,
            proposal,
            source=fixture.source,
            allowed_source_paths=fixture.allowed_source_paths,
        )
    except Exception as exc:
        return _fixture_result(
            fixture,
            proposal_model=proposal_model,
            pipeline_error=_error("proposal_pipeline", proposal_model, exc),
        )

    results = []
    judgments = []
    for reviewer_model in reviewer_models:
        try:
            settings = registry_factory(reviewer_model).require_ready(
                [ProviderCapability.CHAT, ProviderCapability.STRUCTURED_JSON]
            )
            raw_evaluation = await evaluation_client.complete_evaluation(
                settings=settings,
                messages=practice_design_benchmark_messages(
                    fixture.source,
                    proposal,
                    production_review,
                    source_revision=fixture.source_revision,
                ),
            )
            evaluation = validate_practice_design_benchmark_evaluation(
                raw_evaluation,
                proposal=proposal,
                source=fixture.source,
                allowed_source_paths=fixture.allowed_source_paths,
            )
            results.append(
                PracticeDesignBenchmarkReviewerResult(
                    reviewer_model=reviewer_model, evaluation=evaluation
                )
            )
            judgments.append(
                PracticeDesignBenchmarkReviewerJudgment(
                    reviewer_model=reviewer_model, evaluation=evaluation
                )
            )
        except Exception as exc:
            results.append(
                PracticeDesignBenchmarkReviewerResult(
                    reviewer_model=reviewer_model,
                    error=_error("benchmark_review", reviewer_model, exc),
                )
            )
    return _fixture_result(
        fixture,
        proposal_model=proposal_model,
        proposal=proposal,
        production_review=production_review,
        reviewer_results=tuple(results),
        dimension_summaries=summarize_dimension_scores(judgments) if judgments else (),
    )


def _fixture_result(
    fixture: PracticeDesignBenchmarkFixture,
    *,
    proposal_model: str,
    **values: Any,
) -> PracticeDesignBenchmarkFixtureResult:
    return PracticeDesignBenchmarkFixtureResult(
        fixture_id=fixture.id,
        discipline=fixture.discipline,
        domain=fixture.domain,
        provenance=fixture.provenance,
        source_revision=fixture.source_revision,
        proposal_model=proposal_model,
        **values,
    )


def _error(stage: str, model: str, exc: Exception) -> PracticeDesignBenchmarkError:
    message = str(exc).strip() or exc.__class__.__name__
    return PracticeDesignBenchmarkError(stage=stage, model=model, message=message)
