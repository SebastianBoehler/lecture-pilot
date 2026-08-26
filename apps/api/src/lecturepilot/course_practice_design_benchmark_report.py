from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BeforeValidator, Field, model_validator

from lecturepilot.course_practice_design_benchmark_models import (
    BENCHMARK_DIMENSIONS,
    SCORE_ANCHORS,
    BenchmarkDimension,
    PracticeDesignBenchmarkDimensionSummary,
    PracticeDesignBenchmarkEvaluation,
    PracticeDesignBenchmarkReviewerJudgment,
    summarize_dimension_scores,
)
from lecturepilot.course_practice_design_contract import (
    NonblankText,
    StrictPracticeDesignModel,
    freeze_collection,
)
from lecturepilot.course_practice_design_models import PracticeDesignProposal
from lecturepilot.course_practice_design_review_models import PracticeDesignReviewResult


class PracticeDesignBenchmarkScaleAnchor(StrictPracticeDesignModel):
    score: int = Field(ge=1, le=5)
    meaning: NonblankText = Field(max_length=200)


class PracticeDesignBenchmarkError(StrictPracticeDesignModel):
    stage: Literal["proposal_pipeline", "benchmark_review"]
    model: NonblankText = Field(max_length=200)
    message: NonblankText = Field(max_length=4_000)


class PracticeDesignBenchmarkReviewerResult(StrictPracticeDesignModel):
    reviewer_model: NonblankText = Field(max_length=200)
    evaluation: PracticeDesignBenchmarkEvaluation | None = None
    error: PracticeDesignBenchmarkError | None = None

    @model_validator(mode="after")
    def require_evaluation_or_error(self) -> PracticeDesignBenchmarkReviewerResult:
        if (self.evaluation is None) == (self.error is None):
            raise ValueError("Reviewer result needs exactly one evaluation or error.")
        return self


class PracticeDesignBenchmarkFixtureResult(StrictPracticeDesignModel):
    fixture_id: NonblankText = Field(max_length=80)
    discipline: NonblankText = Field(max_length=80)
    domain: Literal["conceptual", "quantitative"]
    provenance: Literal["synthetic", "public"]
    source_revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    proposal_model: NonblankText = Field(max_length=200)
    proposal: PracticeDesignProposal | None = None
    production_review: PracticeDesignReviewResult | None = None
    reviewer_results: Annotated[
        tuple[PracticeDesignBenchmarkReviewerResult, ...], BeforeValidator(freeze_collection)
    ] = ()
    dimension_summaries: Annotated[
        tuple[PracticeDesignBenchmarkDimensionSummary, ...], BeforeValidator(freeze_collection)
    ] = ()
    pipeline_error: PracticeDesignBenchmarkError | None = None

    @model_validator(mode="after")
    def require_complete_success_or_pipeline_error(self) -> PracticeDesignBenchmarkFixtureResult:
        has_output = self.proposal is not None or self.production_review is not None
        if self.pipeline_error is not None:
            if has_output or self.reviewer_results or self.dimension_summaries:
                raise ValueError("A failed proposal pipeline cannot retain fabricated output.")
            if (
                self.pipeline_error.stage != "proposal_pipeline"
                or self.pipeline_error.model != self.proposal_model
            ):
                raise ValueError("Proposal-pipeline error identity is inconsistent.")
            return self
        if self.proposal is None or self.production_review is None:
            raise ValueError("A successful fixture needs proposal and production review output.")
        for result in self.reviewer_results:
            if result.error is not None and (
                result.error.stage != "benchmark_review"
                or result.error.model != result.reviewer_model
            ):
                raise ValueError("Benchmark-review error identity is inconsistent.")
        judgments = tuple(
            PracticeDesignBenchmarkReviewerJudgment(
                reviewer_model=result.reviewer_model,
                evaluation=result.evaluation,
            )
            for result in self.reviewer_results
            if result.evaluation is not None
        )
        expected = summarize_dimension_scores(judgments) if judgments else ()
        if self.dimension_summaries != expected:
            raise ValueError("Fixture dimension summaries do not match reviewer scores.")
        return self


class PracticeDesignBenchmarkReport(StrictPracticeDesignModel):
    schema_version: Literal[1] = 1
    generated_at: datetime
    proposal_model: NonblankText = Field(max_length=200)
    reviewer_models: Annotated[tuple[str, ...], BeforeValidator(freeze_collection)] = Field(
        min_length=2
    )
    dimensions: Annotated[tuple[BenchmarkDimension, ...], BeforeValidator(freeze_collection)] = (
        BENCHMARK_DIMENSIONS
    )
    score_scale: Annotated[
        tuple[PracticeDesignBenchmarkScaleAnchor, ...], BeforeValidator(freeze_collection)
    ] = tuple(
        PracticeDesignBenchmarkScaleAnchor(score=score, meaning=meaning)
        for score, meaning in SCORE_ANCHORS.items()
    )
    fixtures: Annotated[
        tuple[PracticeDesignBenchmarkFixtureResult, ...], BeforeValidator(freeze_collection)
    ] = Field(min_length=1)

    @model_validator(mode="after")
    def require_consistent_model_identity(self) -> PracticeDesignBenchmarkReport:
        if len(set(self.reviewer_models)) != len(self.reviewer_models):
            raise ValueError("At least two distinct reviewer models are required.")
        if self.dimensions != BENCHMARK_DIMENSIONS:
            raise ValueError("Benchmark report dimensions must match the frozen contract.")
        expected_scale = tuple(SCORE_ANCHORS.items())
        if tuple((item.score, item.meaning) for item in self.score_scale) != expected_scale:
            raise ValueError("Benchmark report score anchors must match the frozen scale.")
        for fixture in self.fixtures:
            if fixture.proposal_model != self.proposal_model:
                raise ValueError("Fixture proposal-model identity does not match the report.")
            result_models = tuple(item.reviewer_model for item in fixture.reviewer_results)
            if fixture.pipeline_error is None and result_models != self.reviewer_models:
                raise ValueError("Fixture reviewer-model identities do not match the report.")
        return self

    @property
    def has_errors(self) -> bool:
        return any(
            fixture.pipeline_error is not None
            or any(result.error is not None for result in fixture.reviewer_results)
            for fixture in self.fixtures
        )
