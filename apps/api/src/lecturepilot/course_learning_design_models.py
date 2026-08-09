from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from lecturepilot.learning_map import LearningMap, LearningMapEvidenceCriterion


class LearningDesignApproval(BaseModel):
    approved_by: str = Field(min_length=1, max_length=160)
    approved_at: datetime
    draft_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    learning_map_revision: str = Field(pattern=r"^[a-f0-9]{64}$")


class LearningDesignReview(BaseModel):
    schema_version: int = 1
    course_id: str = Field(min_length=1, max_length=120)
    lecture_id: str = Field(min_length=1, max_length=120)
    draft_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    learning_map: LearningMap
    warnings: list[str] = Field(default_factory=list, max_length=100)
    factual_quality_separate: bool = True
    approval: LearningDesignApproval | None = None


class LearningDesignGateInput(BaseModel):
    id: str = Field(min_length=1, max_length=160)
    prompt: str = Field(min_length=1, max_length=1_000)
    evidence_criteria: list[LearningMapEvidenceCriterion] = Field(min_length=1, max_length=40)
    transfer_prompt: str | None = Field(default=None, max_length=1_000)
    review_after_days: int = Field(ge=1, le=365)


class LearningDesignPrerequisiteInput(BaseModel):
    section_id: str = Field(min_length=1, max_length=160)
    prerequisite_ids: list[str] = Field(default_factory=list, max_length=20)


class LearningDesignUpdate(BaseModel):
    draft_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    learning_map_revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    objective: str = Field(min_length=1, max_length=1_000)
    gates: list[LearningDesignGateInput] = Field(default_factory=list, max_length=100)
    prerequisites: list[LearningDesignPrerequisiteInput] = Field(
        default_factory=list, max_length=200
    )


class LearningDesignApprovalInput(BaseModel):
    draft_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    learning_map_revision: str = Field(pattern=r"^[a-f0-9]{64}$")
