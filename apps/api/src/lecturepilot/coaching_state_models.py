from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from lecturepilot.agent_context_models import AgentConversationMessage
from lecturepilot.models import QualityGateStatus
from lecturepilot.scaffold_policy import AssistanceLevel

AttemptKind = Literal["none", "independent", "supported_retry", "delayed_transfer"]
PendingCheckKind = Literal["standard", "delayed_transfer"]


class PendingCheck(BaseModel):
    gate_id: str = Field(min_length=1, max_length=160)
    gate_revision: str | None = Field(default=None, max_length=64)
    prompt: str = Field(min_length=1, max_length=500)
    assistance_level: AssistanceLevel = "none"
    kind: PendingCheckKind = "standard"
    issued_at: str


class DelayedReview(BaseModel):
    gate_id: str = Field(min_length=1, max_length=160)
    gate_revision: str | None = Field(default=None, max_length=64)
    scheduled_at: str | None = None
    due_at: str
    attempted_at: str | None = None
    completed_at: str | None = None


class CoachingTurnEvent(BaseModel):
    created_at: str
    gate_id: str
    gate_revision: str | None = Field(default=None, max_length=64)
    gate_status: QualityGateStatus
    support_profile: str
    process_label: str
    attempt_kind: AttemptKind = "none"
    attempt_index: int | None = Field(default=None, ge=1)
    assistance_level: AssistanceLevel = "none"
    delay_seconds: int | None = Field(default=None, ge=0)
    independent_attempt: bool = False
    support_before_attempt: bool = False
    transfer_attempt: bool = False
    evidence_ids: list[str] = Field(default_factory=list, max_length=40)
    missing_evidence_ids: list[str] = Field(default_factory=list, max_length=40)


class CoachingProgress(BaseModel):
    session_goal: str = ""
    goal_proposed: bool = False
    turns: list[CoachingTurnEvent] = Field(default_factory=list)
    attempt_counts: dict[str, int] = Field(default_factory=dict)
    attendance_prior_used: bool = False
    messages: list[AgentConversationMessage] = Field(default_factory=list, max_length=8)
    pending_check: PendingCheck | None = None
    delayed_reviews: dict[str, DelayedReview] = Field(default_factory=dict)
    updated_at: str | None = None
