from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from lecturepilot.coaching_state_models import PendingCheckKind
from lecturepilot.quality_gate_models import QualityGateStatus
from lecturepilot.scaffold_policy import AssistanceLevel


class LearnerQuizState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    selected_index: int = Field(ge=0, le=25)
    correct: bool | None = None


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
    gate_statuses: dict[str, QualityGateStatus] = Field(default_factory=dict)
    quiz_states: dict[str, LearnerQuizState] = Field(default_factory=dict)
    active_session_goal: str | None = None
    pending_check: LearnerPendingCheck | None = None
    due_gate_reviews: list[LearnerDueGateReview] = Field(default_factory=list)
