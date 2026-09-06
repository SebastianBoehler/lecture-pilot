from typing import Literal

from pydantic import BaseModel, Field


class AssessmentObservation(BaseModel):
    kind: Literal["readiness", "practice_exam"]
    attempt_id: str
    question_id: str
    created_at: str
    assessment: Literal["automatic_choice_check", "ai_assessment", "ungraded"]
    assistance: Literal["unknown"] = "unknown"
    source_revision: str | None = None
    source_ids: list[str] = Field(default_factory=list)
    section_id: str | None = None
    prompt: str | None = Field(default=None, max_length=800)
    answer: str | None = Field(default=None, max_length=1600)
    correct: bool | None = None
    score: float | None = None
    feedback: str | None = Field(default=None, max_length=600)
    excerpted: bool = False


class AssessmentHistoryContext(BaseModel):
    observations: list[AssessmentObservation] = Field(default_factory=list, max_length=12)
    has_more: bool = False
