from __future__ import annotations

from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from lecturepilot.coaching_state_models import PendingCheckKind
from lecturepilot.quality_gate_models import QualityGateStatus
from lecturepilot.scaffold_policy import AssistanceLevel

QuizOutcome = Literal["correct", "incorrect", "unscored"]
QuizCorrectionState = Literal["not_needed", "needed", "corrected"]


class LearnerQuizState(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    selected_index: int = Field(ge=0, le=25)
    correct: bool | None
    publication_version: int = Field(ge=1)
    attempt_index: int = Field(ge=1)
    first_attempt_correct: bool | None
    latest_outcome: QuizOutcome
    correction_state: QuizCorrectionState


class LearnerQuizStorePayload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    course_id: str = Field(min_length=1, max_length=120)
    lecture_id: str = Field(min_length=1, max_length=120)
    updated_at: AwareDatetime
    quizzes: dict[str, LearnerQuizState]
    attempts: dict[str, dict[str, LearnerQuizState]]


class LearnerPendingCheck(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    gate_id: str
    gate_revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    prompt: str
    assistance_level: AssistanceLevel
    kind: PendingCheckKind


class LearnerDueGateReview(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    gate_id: str
    gate_revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    due_at: AwareDatetime


class LearnerLessonState(BaseModel):
    course_id: str
    lecture_id: str
    publication_version: int = Field(strict=True, ge=1)
    gate_statuses: dict[str, QualityGateStatus] = Field(default_factory=dict)
    quiz_states: dict[str, LearnerQuizState] = Field(default_factory=dict)
    active_session_goal: str | None = None
    pending_check: LearnerPendingCheck | None = None
    due_gate_reviews: list[LearnerDueGateReview] = Field(default_factory=list)
