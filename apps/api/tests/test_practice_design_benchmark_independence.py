from pathlib import Path

import pytest

from lecturepilot.course_practice_design_benchmark_fixtures import (
    load_practice_design_benchmark_fixtures,
)
from lecturepilot.course_practice_design_benchmark_models import (
    PracticeDesignBenchmarkReviewerSpec,
)
from lecturepilot.course_practice_design_benchmark_runner import run_practice_design_benchmark


FIXTURES = Path(__file__).resolve().parents[3] / "benchmarks/practice-design/fixtures.json"


@pytest.mark.parametrize(
    ("reviewer_model", "reviewer_identity", "error"),
    [
        (
            "OPENAI/PROPOSAL-MODEL",
            "vendor/reviewer-model@1",
            "proposal and reviewer invocation model slugs",
        ),
        (
            "openrouter/vendor/proposal-model",
            "VENDOR/PROPOSAL-MODEL@2026-08-01",
            "proposal and reviewer underlying model identities",
        ),
    ],
)
@pytest.mark.asyncio
async def test_runner_rejects_proposal_model_as_its_own_reviewer(
    reviewer_model: str, reviewer_identity: str, error: str
) -> None:
    reviewers = (
        PracticeDesignBenchmarkReviewerSpec(
            invocation_model=reviewer_model,
            underlying_model_identity=reviewer_identity,
        ),
        PracticeDesignBenchmarkReviewerSpec(
            invocation_model="gemini/independent-reviewer",
            underlying_model_identity="google/independent-reviewer@1",
        ),
    )

    with pytest.raises(ValueError, match=f"(?i){error}"):
        await run_practice_design_benchmark(
            fixtures=(load_practice_design_benchmark_fixtures(FIXTURES)[0],),
            proposal_model="openai/proposal-model",
            proposal_underlying_model_identity="vendor/proposal-model@2026-08-01",
            reviewers=reviewers,
            planner=_PlannerThatMustNotRun(),
        )


class _PlannerThatMustNotRun:
    async def propose(self, **_kwargs):
        raise AssertionError("Model independence must be validated before proposal generation.")
