from __future__ import annotations

from collections.abc import Sequence
from typing import Annotated, Literal

from pydantic import BeforeValidator, Field, model_validator

from lecturepilot.course_practice_design_contract import (
    NonblankText,
    StrictPracticeDesignModel,
    freeze_collection,
)
from lecturepilot.course_practice_design_evidence import PracticeSourceAnchor


BenchmarkDimension = Literal[
    "source_faithfulness",
    "measurable_outcomes",
    "task_answerability",
    "exit_equivalence",
    "transfer_invariant_novelty",
    "rubric_sufficiency",
    "hint_leakage",
    "misconception_plausibility",
    "source_coverage",
]
BENCHMARK_DIMENSIONS: tuple[BenchmarkDimension, ...] = (
    "source_faithfulness",
    "measurable_outcomes",
    "task_answerability",
    "exit_equivalence",
    "transfer_invariant_novelty",
    "rubric_sufficiency",
    "hint_leakage",
    "misconception_plausibility",
    "source_coverage",
)
SCORE_ANCHORS: dict[int, str] = {
    1: "Unusable: contradicted, unsupported, leaked, or not assessable.",
    2: "Major defects: substantial repair is needed before use.",
    3: "Mixed: usable elements remain, but a material weakness persists.",
    4: "Sound: no major defect, with a minor specific limitation.",
    5: "Strong: fully satisfies the dimension with no material defect found.",
}


class PracticeDesignBenchmarkFailureExample(StrictPracticeDesignModel):
    scope: Literal["target", "global"]
    description: NonblankText = Field(max_length=2_000)
    target_ids: Annotated[tuple[str, ...], BeforeValidator(freeze_collection)] = Field(max_length=8)
    supporting_anchors: Annotated[
        tuple[PracticeSourceAnchor, ...], BeforeValidator(freeze_collection)
    ] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def require_explicit_scope(self) -> PracticeDesignBenchmarkFailureExample:
        if len(set(self.target_ids)) != len(self.target_ids):
            raise ValueError("Benchmark failure-example target IDs must be unique.")
        if self.scope == "target" and not self.target_ids:
            raise ValueError("Target-scoped failure examples need at least one target ID.")
        if self.scope == "global" and self.target_ids:
            raise ValueError("Global failure examples cannot name target IDs.")
        return self


class PracticeDesignBenchmarkScore(StrictPracticeDesignModel):
    dimension: BenchmarkDimension
    score: int = Field(ge=1, le=5)
    rationale: NonblankText = Field(max_length=3_000)
    failure_examples: Annotated[
        tuple[PracticeDesignBenchmarkFailureExample, ...], BeforeValidator(freeze_collection)
    ] = Field(max_length=8)

    @model_validator(mode="after")
    def require_examples_for_limitations(self) -> PracticeDesignBenchmarkScore:
        if self.score < 5 and not self.failure_examples:
            raise ValueError("Every submaximal score needs a source-supported failure example.")
        if self.score == 5 and self.failure_examples:
            raise ValueError("A maximum score cannot retain a failure example.")
        return self


class PracticeDesignBenchmarkEvaluation(StrictPracticeDesignModel):
    scores: Annotated[
        tuple[PracticeDesignBenchmarkScore, ...], BeforeValidator(freeze_collection)
    ] = Field(min_length=len(BENCHMARK_DIMENSIONS), max_length=len(BENCHMARK_DIMENSIONS))

    @model_validator(mode="after")
    def require_complete_ordered_dimensions(self) -> PracticeDesignBenchmarkEvaluation:
        if tuple(score.dimension for score in self.scores) != BENCHMARK_DIMENSIONS:
            raise ValueError(
                "Evaluation must cover every benchmark dimension exactly once in order."
            )
        return self


class PracticeDesignBenchmarkReviewerSpec(StrictPracticeDesignModel):
    invocation_model: NonblankText = Field(
        max_length=200,
        description=(
            "Configured provider/model slug used for this invocation. Slugs must be unique for "
            "configuration consistency but do not establish reviewer independence."
        ),
    )
    underlying_model_identity: NonblankText = Field(
        max_length=300,
        description=(
            "Operator-supplied canonical underlying model and version, or materially distinct "
            "fine-tune identity. Gateways, endpoints, regions, and deployments serving the "
            "same weights must use the same value."
        ),
    )
    deployment_provenance: NonblankText | None = Field(
        default=None,
        max_length=300,
        description=(
            "Optional gateway, endpoint, region, or deployment provenance retained for audit; "
            "never used to establish reviewer distinctness."
        ),
    )


class PracticeDesignBenchmarkReviewerJudgment(StrictPracticeDesignModel):
    reviewer: PracticeDesignBenchmarkReviewerSpec
    evaluation: PracticeDesignBenchmarkEvaluation


class PracticeDesignBenchmarkReviewerScore(StrictPracticeDesignModel):
    reviewer: PracticeDesignBenchmarkReviewerSpec
    score: int = Field(ge=1, le=5)


class PracticeDesignBenchmarkDimensionSummary(StrictPracticeDesignModel):
    dimension: BenchmarkDimension
    reviewer_scores: Annotated[
        tuple[PracticeDesignBenchmarkReviewerScore, ...], BeforeValidator(freeze_collection)
    ] = Field(min_length=1)
    mean_score: float = Field(ge=1, le=5)
    minimum_score: int = Field(ge=1, le=5)
    maximum_score: int = Field(ge=1, le=5)
    score_spread: int | None = Field(default=None, ge=0, le=4)


def summarize_dimension_scores(
    judgments: Sequence[PracticeDesignBenchmarkReviewerJudgment],
) -> tuple[PracticeDesignBenchmarkDimensionSummary, ...]:
    validate_reviewer_specs(tuple(judgment.reviewer for judgment in judgments), minimum=1)
    summaries = []
    for index, dimension in enumerate(BENCHMARK_DIMENSIONS):
        reviewer_scores = tuple(
            PracticeDesignBenchmarkReviewerScore(
                reviewer=judgment.reviewer,
                score=judgment.evaluation.scores[index].score,
            )
            for judgment in judgments
        )
        values = [item.score for item in reviewer_scores]
        summaries.append(
            PracticeDesignBenchmarkDimensionSummary(
                dimension=dimension,
                reviewer_scores=reviewer_scores,
                mean_score=round(sum(values) / len(values), 3),
                minimum_score=min(values),
                maximum_score=max(values),
                score_spread=max(values) - min(values) if len(values) >= 2 else None,
            )
        )
    return tuple(summaries)


def validate_reviewer_specs(
    reviewers: Sequence[PracticeDesignBenchmarkReviewerSpec], *, minimum: int = 2
) -> tuple[PracticeDesignBenchmarkReviewerSpec, ...]:
    reviewers = tuple(reviewers)
    if len(reviewers) < minimum:
        raise ValueError(f"Provide at least {minimum} reviewer specifications.")
    invocation_keys = [
        " ".join(reviewer.invocation_model.split()).casefold() for reviewer in reviewers
    ]
    if len(set(invocation_keys)) != len(invocation_keys):
        raise ValueError("Reviewer invocation model slugs must be distinct.")
    underlying_identity_keys = [
        " ".join(reviewer.underlying_model_identity.split()).casefold() for reviewer in reviewers
    ]
    if len(set(underlying_identity_keys)) != len(underlying_identity_keys):
        raise ValueError("Underlying reviewer model identities must be distinct.")
    return reviewers
