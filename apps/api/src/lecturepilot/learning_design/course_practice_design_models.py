from __future__ import annotations

from typing import Annotated, Literal

from pydantic import (
    BeforeValidator,
    Field,
    ValidationInfo,
    model_validator,
)

from lecturepilot.learning_design.canonical_digest import canonical_json_digest
from lecturepilot.learning_design.course_learning_intent import LearningIntent
from lecturepilot.learning_design.course_practice_design_context import PracticePlanningContext
from lecturepilot.learning_design.course_practice_design_contract import (
    NonblankText,
    StrictPracticeDesignModel,
    freeze_collection,
)
from lecturepilot.learning_design.course_practice_design_review_models import (
    PracticeDesignQualityReview,
)

from lecturepilot.learning_design.course_practice_target import (
    PracticeEvidenceCriterion as PracticeEvidenceCriterion,
    PracticeHint as PracticeHint,
    PracticeMisconception as PracticeMisconception,
    PracticeTarget as PracticeTarget,
    require_unique_ids,
)

_REVISION_PATTERN = r"^[a-f0-9]{64}$"


class PracticeDesignProposal(StrictPracticeDesignModel):
    lecture_title: NonblankText = Field(min_length=1, max_length=200)
    objective: NonblankText = Field(min_length=1, max_length=1_000)
    planning_context: PracticePlanningContext
    targets: Annotated[tuple[PracticeTarget, ...], BeforeValidator(freeze_collection)] = Field(
        min_length=1, max_length=8
    )

    @model_validator(mode="after")
    def validate_target_ids(self) -> PracticeDesignProposal:
        require_unique_ids(self.targets, "practice target")
        return self


class PracticeDesign(StrictPracticeDesignModel):
    schema_version: Literal[2] = 2
    learning_intent: LearningIntent
    course_id: str = Field(min_length=1, max_length=120)
    lecture_id: str = Field(min_length=1, max_length=120)
    lecture_title: NonblankText = Field(min_length=1, max_length=200)
    objective: NonblankText = Field(min_length=1, max_length=1_000)
    planning_context: PracticePlanningContext
    source_revision: str = Field(pattern=_REVISION_PATTERN)
    targets: Annotated[tuple[PracticeTarget, ...], BeforeValidator(freeze_collection)] = Field(
        max_length=8
    )
    revision: str = Field(pattern=_REVISION_PATTERN)
    quality_review: PracticeDesignQualityReview | None = None

    @model_validator(mode="after")
    def validate_revision(self, info: ValidationInfo) -> PracticeDesign:
        if not (info.context or {}).get(
            "build_revision"
        ) and self.revision != practice_design_revision(self):
            raise ValueError("Practice design revision is invalid.")
        require_unique_ids(self.targets, "practice target")
        if self.learning_intent.source_revision != self.source_revision:
            raise ValueError("Learning intent source revision is stale.")
        if self.targets:
            self.learning_intent.require_matches(self)
        elif (
            self.objective != self.learning_intent.objective
            or self.planning_context != self.learning_intent.planning_context
        ):
            raise ValueError("Pending teaching must retain protected learning intent.")
        return self

    @classmethod
    def create(cls, **values: object) -> PracticeDesign:
        candidate = cls.model_validate(
            {**values, "revision": "0" * 64}, context={"build_revision": True}
        )
        payload = _revision_payload(candidate)
        return cls.model_validate(
            {**candidate.model_dump(mode="python"), "revision": canonical_json_digest(payload)}
        )


def practice_design_revision(design: PracticeDesign) -> str:
    return canonical_json_digest(_revision_payload(design))


def _revision_payload(design: PracticeDesign) -> dict:
    # Goal approval is excluded: approving identical content keeps the design revision.
    payload = design.model_dump(mode="json", exclude={"revision", "quality_review"})
    payload["learning_intent"].pop("approval", None)
    return payload
