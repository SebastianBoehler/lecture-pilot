from __future__ import annotations

from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from lecturepilot.agent_context_models import AgentConversationMessage
from lecturepilot.scaffold_policy import AssistanceLevel

AttemptKind = Literal["none", "independent", "supported_retry", "delayed_transfer"]
AssessedAttemptKind = Literal["independent", "supported_retry", "delayed_transfer"]
PendingCheckKind = Literal["standard", "delayed_transfer"]
GateStatus = Literal["passed", "needs_evidence"]


class PendingCheck(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    gate_id: str = Field(min_length=1, max_length=160)
    gate_revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    prompt: str = Field(min_length=1, max_length=500)
    assistance_level: AssistanceLevel
    kind: PendingCheckKind
    issued_at: AwareDatetime


class DelayedReview(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    gate_id: str = Field(min_length=1, max_length=160)
    gate_revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    section_id: str = Field(min_length=1, max_length=160)
    transfer_prompt: str = Field(min_length=1, max_length=1000)
    scheduled_at: AwareDatetime
    due_at: AwareDatetime
    planned_delay_seconds: int = Field(gt=0)
    attempted_at: AwareDatetime | None
    completed_at: AwareDatetime | None
    observed_delay_seconds: int | None = Field(ge=0)


class CoachingTurnEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    created_at: AwareDatetime
    gate_id: str = Field(min_length=1, max_length=160)
    gate_revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    gate_status: GateStatus
    support_profile: str = Field(min_length=1, max_length=160)
    process_label: str = Field(min_length=1, max_length=160)
    attempt_kind: AssessedAttemptKind
    attempt_index: int = Field(ge=1)
    assistance_level: AssistanceLevel
    planned_delay_seconds: int | None = Field(ge=0)
    observed_delay_seconds: int | None = Field(ge=0)
    evidence_ids: list[str] = Field(max_length=40)
    missing_evidence_ids: list[str] = Field(max_length=40)


class CoachingProgress(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal[1]
    course_id: str = Field(min_length=1, max_length=120)
    lecture_id: str = Field(min_length=1, max_length=120)
    session_goal: str | None = Field(max_length=500)
    turns: list[CoachingTurnEvent] = Field(max_length=200)
    attempt_counts: dict[str, int]
    attendance_prior_used: bool
    messages: list[AgentConversationMessage] = Field(max_length=8)
    pending_check: PendingCheck | None
    delayed_reviews: dict[str, DelayedReview]
    updated_at: AwareDatetime | None

    @model_validator(mode="after")
    def validate_review_keys(self) -> CoachingProgress:
        for key, review in self.delayed_reviews.items():
            if key != review_key(review.gate_id, review.gate_revision):
                raise ValueError("Delayed-review key does not match its gate contract.")
        return self

    @classmethod
    def empty(cls, *, course_id: str, lecture_id: str) -> CoachingProgress:
        return cls(
            schema_version=1,
            course_id=course_id,
            lecture_id=lecture_id,
            session_goal=None,
            turns=[],
            attempt_counts={},
            attendance_prior_used=False,
            messages=[],
            pending_check=None,
            delayed_reviews={},
            updated_at=None,
        )


def review_key(gate_id: str, gate_revision: str) -> str:
    return f"{gate_id}@{gate_revision}"


def attempt_key(gate_id: str, gate_revision: str) -> str:
    return review_key(gate_id, gate_revision)
