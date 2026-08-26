from datetime import UTC, datetime
from pathlib import Path

import pytest

from lecturepilot.course_practice_design_benchmark_fixtures import (
    load_practice_design_benchmark_fixtures,
)
from lecturepilot.course_practice_design_benchmark_models import (
    BENCHMARK_DIMENSIONS,
    PracticeDesignBenchmarkReviewerSpec,
)
from lecturepilot.course_practice_design_benchmark_report import PracticeDesignBenchmarkReport
from lecturepilot.course_practice_design_benchmark_runner import run_practice_design_benchmark
from lecturepilot.course_practice_design_planner import ReviewedPracticeDesignProposal
from lecturepilot.model_client import ModelExecutionError
from practice_design_review_test_helpers import passing_review
from practice_design_test_helpers import proposal, target


FIXTURES = Path(__file__).resolve().parents[3] / "benchmarks/practice-design/fixtures.json"


@pytest.mark.asyncio
async def test_runner_retains_production_output_per_reviewer_scores_and_disagreement() -> None:
    fixture = load_practice_design_benchmark_fixtures(FIXTURES)[0]
    planner = _Planner(_reviewed_proposal(fixture))
    client = _EvaluationClient()

    report = await run_practice_design_benchmark(
        fixtures=(fixture,),
        proposal_model="openai/proposal-model",
        reviewers=_reviewers(),
        planner=planner,
        evaluation_client=client,
        registry_factory=_Registry,
        generated_at=datetime(2026, 8, 26, 12, tzinfo=UTC),
    )

    assert planner.calls == [
        (fixture.source_revision, fixture.allowed_source_paths, fixture.source)
    ]
    assert client.models == ["openai/reviewer-a", "gemini/reviewer-b"]
    result = report.fixtures[0]
    assert result.proposal_model == "openai/proposal-model"
    assert result.proposal is not None
    assert result.production_review == passing_review()
    assert tuple(item.reviewer for item in result.reviewer_results) == _reviewers()
    assert result.dimension_summaries[0].score_spread == 3
    assert PracticeDesignBenchmarkReport.model_validate_json(report.model_dump_json()) == report


@pytest.mark.asyncio
async def test_runner_records_provider_errors_without_fallback_scores() -> None:
    fixture = load_practice_design_benchmark_fixtures(FIXTURES)[0]
    client = _EvaluationClient(failing_model="openai/reviewer-a")

    report = await run_practice_design_benchmark(
        fixtures=(fixture,),
        proposal_model="openai/proposal-model",
        reviewers=_reviewers(),
        planner=_Planner(_reviewed_proposal(fixture)),
        evaluation_client=client,
        registry_factory=_Registry,
    )

    result = report.fixtures[0]
    assert result.reviewer_results[0].evaluation is None
    assert result.reviewer_results[0].error is not None
    assert result.reviewer_results[0].error.message == "reviewer unavailable"
    assert result.reviewer_results[1].evaluation is not None
    assert result.dimension_summaries[0].score_spread is None
    assert result.dimension_summaries[0].reviewer_scores[0].reviewer == _reviewers()[1]


@pytest.mark.asyncio
async def test_runner_records_proposal_pipeline_errors_without_calling_reviewers() -> None:
    fixture = load_practice_design_benchmark_fixtures(FIXTURES)[0]
    client = _EvaluationClient()

    report = await run_practice_design_benchmark(
        fixtures=(fixture,),
        proposal_model="openai/proposal-model",
        reviewers=_reviewers(),
        planner=_FailingPlanner(),
        evaluation_client=client,
        registry_factory=_Registry,
    )

    result = report.fixtures[0]
    assert result.proposal is None
    assert result.production_review is None
    assert result.pipeline_error is not None
    assert result.pipeline_error.message == "proposal unavailable"
    assert result.reviewer_results == ()
    assert result.dimension_summaries == ()
    assert client.models == []
    assert report.has_errors is True


@pytest.mark.asyncio
async def test_runner_rejects_aliases_with_the_same_canonical_reviewer_identity() -> None:
    fixture = load_practice_design_benchmark_fixtures(FIXTURES)[0]
    reviewers = (
        PracticeDesignBenchmarkReviewerSpec(
            invocation_model="openai/gpt-5.6",
            canonical_identity="openai/gpt-5.6@2026-08-01",
        ),
        PracticeDesignBenchmarkReviewerSpec(
            invocation_model="openrouter/openai/gpt-5.6",
            canonical_identity="OpenAI/GPT-5.6@2026-08-01",
        ),
    )

    with pytest.raises(ValueError, match="(?i)canonical reviewer identities"):
        await run_practice_design_benchmark(
            fixtures=(fixture,),
            proposal_model="openai/proposal-model",
            reviewers=reviewers,
            planner=_FailingPlanner(),
            evaluation_client=_EvaluationClient(),
            registry_factory=_Registry,
        )


class _Planner:
    def __init__(self, result: ReviewedPracticeDesignProposal) -> None:
        self.result = result
        self.calls = []

    async def propose(self, *, source, source_revision, allowed_source_paths):
        self.calls.append((source_revision, allowed_source_paths, source))
        return self.result


class _FailingPlanner:
    async def propose(self, **_kwargs):
        raise ModelExecutionError("proposal unavailable")


class _EvaluationClient:
    def __init__(self, failing_model: str | None = None) -> None:
        self.failing_model = failing_model
        self.models: list[str] = []

    async def complete_evaluation(self, *, settings, **_kwargs) -> dict:
        self.models.append(settings.model)
        if settings.model == self.failing_model:
            raise ModelExecutionError("reviewer unavailable")
        default_score = 2 if settings.model == "openai/reviewer-a" else 5
        return _evaluation_payload(default_score)


class _Registry:
    def __init__(self, model: str) -> None:
        self.model = model

    def require_ready(self, _capabilities):
        return type(
            "Settings",
            (),
            {"model": self.model, "provider": self.model.split("/", 1)[0]},
        )()


def _reviewed_proposal(fixture) -> ReviewedPracticeDesignProposal:
    source_path = fixture.allowed_source_paths[0]
    excerpt = fixture.source.sections[0].blocks[0].text
    source_target = target(source_refs=(source_path,), source_excerpt=excerpt)
    return ReviewedPracticeDesignProposal(
        proposal=proposal().model_copy(update={"targets": (source_target,)}),
        review=passing_review(),
    )


def _reviewers() -> tuple[PracticeDesignBenchmarkReviewerSpec, ...]:
    return (
        PracticeDesignBenchmarkReviewerSpec(
            invocation_model="openai/reviewer-a",
            canonical_identity="vendor/model-a@1",
        ),
        PracticeDesignBenchmarkReviewerSpec(
            invocation_model="gemini/reviewer-b",
            canonical_identity="vendor/model-b@1",
        ),
    )


def _evaluation_payload(score: int) -> dict:
    return {
        "scores": [
            {
                "dimension": dimension,
                "score": score,
                "rationale": "The reviewer checked the complete proposal and source.",
                "failure_examples": (
                    []
                    if score == 5
                    else [
                        {
                            "scope": "target",
                            "description": "The proposed condition needs material repair.",
                            "target_ids": ["derive-conclusion"],
                            "supporting_anchors": [
                                {
                                    "source_path": "synthetic/biology-natural-selection.md",
                                    "excerpt": ("Audience: introductory undergraduate biology."),
                                }
                            ],
                        }
                    ]
                ),
            }
            for dimension in BENCHMARK_DIMENSIONS
        ]
    }
