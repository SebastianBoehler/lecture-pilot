from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from lecturepilot.coaching_state_models import PendingCheckKind
from lecturepilot.quality_gate_models import QualityGateStatus
from lecturepilot.scaffold_policy import AssistanceLevel

QuizOutcome = Literal["correct", "incorrect", "unscored"]
QuizCorrectionState = Literal["not_needed", "needed", "corrected"]


class LearnerQuizState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    selected_index: int = Field(ge=0, le=25)
    correct: bool | None = None
    publication_version: int = Field(default=1, ge=1)
    attempt_index: int = Field(default=1, ge=1)
    first_attempt_correct: bool | None = None
    latest_outcome: QuizOutcome = "unscored"
    correction_state: QuizCorrectionState = "not_needed"

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_state(cls, value):
        if not isinstance(value, dict):
            return value
        migrated = dict(value)
        correct = migrated.get("correct")
        migrated.setdefault("first_attempt_correct", correct)
        migrated.setdefault(
            "latest_outcome",
            "correct" if correct is True else "incorrect" if correct is False else "unscored",
        )
        migrated.setdefault("correction_state", "needed" if correct is False else "not_needed")
        return migrated


class LearnerPendingCheck(BaseModel):
    gate_id: str
    gate_revision: str | None = None
    prompt: str
    assistance_level: AssistanceLevel
    kind: PendingCheckKind


class LearnerDueGateReview(BaseModel):
    gate_id: str
    gate_revision: str | None = None
    due_at: str


class LearnerLessonState(BaseModel):
    course_id: str
    lecture_id: str
    publication_version: int = Field(strict=True, ge=1)
    gate_statuses: dict[str, QualityGateStatus] = Field(default_factory=dict)
    quiz_states: dict[str, LearnerQuizState] = Field(default_factory=dict)
    active_session_goal: str | None = None
    pending_check: LearnerPendingCheck | None = None
    due_gate_reviews: list[LearnerDueGateReview] = Field(default_factory=list)
