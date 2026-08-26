from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BeforeValidator, Field, model_validator

from lecturepilot.course_practice_design_contract import (
    NonblankText,
    StrictPracticeDesignModel,
    freeze_collection,
)
from lecturepilot.course_practice_design_evidence import PracticeSourceAnchor


ReviewDimension = Literal[
    "source_entailment",
    "objective_task_alignment",
    "exit_equivalence",
    "answer_leakage",
    "difficulty_drift",
    "transfer_invariant_novelty",
    "rubric_sufficiency",
    "target_source_coverage",
]
REVIEW_DIMENSIONS: tuple[ReviewDimension, ...] = (
    "source_entailment",
    "objective_task_alignment",
    "exit_equivalence",
    "answer_leakage",
    "difficulty_drift",
    "transfer_invariant_novelty",
    "rubric_sufficiency",
    "target_source_coverage",
)


class PracticeDesignReviewCheck(StrictPracticeDesignModel):
    dimension: ReviewDimension
    severity: Literal["pass", "warning", "critical"]
    summary: NonblankText = Field(min_length=1, max_length=2_000)
    target_ids: Annotated[tuple[str, ...], BeforeValidator(freeze_collection)] = Field(max_length=8)
    supporting_anchors: Annotated[
        tuple[PracticeSourceAnchor, ...], BeforeValidator(freeze_collection)
    ] = Field(max_length=12)

    @model_validator(mode="after")
    def require_issue_support(self) -> PracticeDesignReviewCheck:
        if self.severity != "pass" and not self.supporting_anchors:
            raise ValueError("Semantic review warnings and critical issues need source support.")
        if len(set(self.target_ids)) != len(self.target_ids):
            raise ValueError("Semantic review target IDs must be unique.")
        return self


class PracticeDesignReviewResult(StrictPracticeDesignModel):
    checks: Annotated[tuple[PracticeDesignReviewCheck, ...], BeforeValidator(freeze_collection)] = (
        Field(min_length=len(REVIEW_DIMENSIONS), max_length=len(REVIEW_DIMENSIONS))
    )

    @model_validator(mode="after")
    def require_complete_ordered_dimensions(self) -> PracticeDesignReviewResult:
        if tuple(check.dimension for check in self.checks) != REVIEW_DIMENSIONS:
            raise ValueError("Semantic review must cover every dimension exactly once in order.")
        return self


class PracticeDesignQualityReview(StrictPracticeDesignModel):
    source_revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    practice_design_revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    checks: Annotated[tuple[PracticeDesignReviewCheck, ...], BeforeValidator(freeze_collection)] = (
        Field(min_length=len(REVIEW_DIMENSIONS), max_length=len(REVIEW_DIMENSIONS))
    )

    @model_validator(mode="after")
    def require_complete_ordered_dimensions(self) -> PracticeDesignQualityReview:
        PracticeDesignReviewResult(checks=self.checks)
        return self

    @property
    def has_critical_issues(self) -> bool:
        return any(check.severity == "critical" for check in self.checks)

    @classmethod
    def bind(
        cls,
        result: PracticeDesignReviewResult,
        *,
        source_revision: str,
        practice_design_revision: str,
    ) -> PracticeDesignQualityReview:
        return cls(
            source_revision=source_revision,
            practice_design_revision=practice_design_revision,
            checks=result.checks,
        )
