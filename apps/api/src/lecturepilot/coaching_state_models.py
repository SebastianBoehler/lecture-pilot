from __future__ import annotations

from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from lecturepilot.coaching_goal_evidence import GoalEvidence
from lecturepilot.coaching_task_bank import TaskExposure

from lecturepilot.agent_context_models import AgentConversationMessage
from lecturepilot.coaching_contract import (
    MAX_APPROVED_TASK_LENGTH,
    AssessmentStage,
    AssistanceLevel,
    HintLevel,
)

AttemptKind = Literal[
    "none",
    "diagnostic",
    "independent",
    "independent_exit",
    "supported_retry",
    "delayed_transfer",
]
AssessedAttemptKind = Literal[
    "diagnostic",
    "independent",
    "independent_exit",
    "supported_retry",
    "delayed_transfer",
]
PendingCheckKind = Literal["standard", "delayed_transfer"]
GateStatus = Literal["passed", "needs_evidence"]


class PendingCheck(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    gate_id: str = Field(min_length=1, max_length=160)
    gate_revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    prompt: str = Field(min_length=1, max_length=MAX_APPROVED_TASK_LENGTH)
    assistance_level: AssistanceLevel
    assistance_content: str | None = Field(max_length=2_000)
    kind: PendingCheckKind
    stage: AssessmentStage
    task_id: str | None = Field(default=None, min_length=1, max_length=80)
    bank_exhausted: bool = False
    issued_at: AwareDatetime

    @model_validator(mode="after")
    def validate_assistance_and_stage(self) -> PendingCheck:
        if self.assistance_level == "none" and self.assistance_content is not None:
            raise ValueError("Unassisted pending checks cannot bind assistance content.")
        if self.assistance_level != "none" and not (
            self.assistance_content and self.assistance_content.strip()
        ):
            raise ValueError("Assisted pending checks require exact assistance content.")
        if self.bank_exhausted and not self.stage.endswith("support"):
            raise ValueError("An exhausted task bank requires supported study.")
        expected_kind = "delayed_transfer" if self.stage == "delayed_transfer" else "standard"
        if self.kind != expected_kind:
            raise ValueError("Pending-check kind does not match its assessment stage.")
        if self.stage in {"diagnostic", "independent_exit", "delayed_transfer"} and (
            self.assistance_level != "none"
        ):
            raise ValueError("Independent assessment stages cannot carry assistance.")
        return self


class HintExposure(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    gate_id: str = Field(min_length=1, max_length=160)
    gate_revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    assistance_level: HintLevel
    content: str = Field(min_length=1, max_length=2_000)
    exposed_at: AwareDatetime


class DelayedReview(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    gate_id: str = Field(min_length=1, max_length=160)
    gate_revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    section_id: str = Field(min_length=1, max_length=160)
    transfer_prompt: str = Field(min_length=1, max_length=MAX_APPROVED_TASK_LENGTH)
    scheduled_at: AwareDatetime
    due_at: AwareDatetime
    planned_delay_seconds: int = Field(gt=0)
    attempted_at: AwareDatetime | None
    completed_at: AwareDatetime | None
    observed_delay_seconds: int | None = Field(ge=0)


class CoachingTurnEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    task_id: str | None = Field(default=None, min_length=1, max_length=80)
    created_at: AwareDatetime
    gate_id: str = Field(min_length=1, max_length=160)
    gate_revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    gate_status: GateStatus
    selected_support_level: AssistanceLevel | None = None
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

    schema_version: Literal[2]
    course_id: str = Field(min_length=1, max_length=120)
    lecture_id: str = Field(min_length=1, max_length=120)
    session_goal: str | None = Field(max_length=500)
    turns: list[CoachingTurnEvent] = Field(max_length=200)
    attempt_counts: dict[str, int]
    attendance_prior_used: bool
    messages: list[AgentConversationMessage] = Field(max_length=8)
    pending_check: PendingCheck | None
    hint_exposures: dict[str, HintExposure]
    delayed_reviews: dict[str, DelayedReview]
    goal_evidence: dict[str, GoalEvidence] = Field(default_factory=dict)
    task_exposures: dict[str, TaskExposure] = Field(default_factory=dict)
    updated_at: AwareDatetime | None

    @model_validator(mode="after")
    def validate_review_keys(self) -> CoachingProgress:
        for key, review in self.delayed_reviews.items():
            if key != review_key(review.gate_id, review.gate_revision):
                raise ValueError("Delayed-review key does not match its gate contract.")
        for key, exposure in self.hint_exposures.items():
            if key != hint_exposure_key(exposure.gate_revision, exposure.assistance_level):
                raise ValueError("Hint-exposure key does not match its gate contract.")
        return self

    @classmethod
    def empty(cls, *, course_id: str, lecture_id: str) -> CoachingProgress:
        return cls(
            schema_version=2,
            course_id=course_id,
            lecture_id=lecture_id,
            session_goal=None,
            turns=[],
            attempt_counts={},
            attendance_prior_used=False,
            messages=[],
            pending_check=None,
            hint_exposures={},
            delayed_reviews={},
            updated_at=None,
        )


def review_key(gate_id: str, gate_revision: str) -> str:
    return f"{gate_id}@{gate_revision}"


def attempt_key(gate_id: str, gate_revision: str, attempt_kind: str) -> str:
    return f"{review_key(gate_id, gate_revision)}@{attempt_kind}"


def hint_exposure_key(gate_revision: str, assistance_level: HintLevel) -> str:
    return f"{gate_revision}@{assistance_level}"
