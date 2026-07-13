from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, Field, ValidationError

from lecturepilot.models import (
    AgentCoachingContext,
    QualityGateDecision,
    QualityGateStatus,
)
from lecturepilot.scaffold_policy import TutorScaffoldPolicy
from lecturepilot.storage_layout import StorageLayout

TRANSFER_DELAY = timedelta(days=2)
MAX_TURN_EVENTS = 200


class CoachingTurnEvent(BaseModel):
    created_at: str
    gate_id: str
    gate_status: QualityGateStatus
    support_profile: str
    process_label: str
    independent_attempt: bool


class DelayedTransferCheck(BaseModel):
    gate_id: str
    due_at: str
    completed_at: str | None = None


class CoachingProgress(BaseModel):
    session_goal: str = ""
    goal_proposed: bool = False
    turns: list[CoachingTurnEvent] = Field(default_factory=list)
    delayed_transfer: DelayedTransferCheck | None = None
    updated_at: str | None = None


class CoachingProgressStore:
    def __init__(self, layout: StorageLayout) -> None:
        self.layout = layout

    def read(self, *, user_id: str, course_id: str, lecture_id: str) -> CoachingProgress:
        path = self._path(user_id=user_id, course_id=course_id, lecture_id=lecture_id)
        if not path.exists():
            return CoachingProgress()
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return CoachingProgress()
        try:
            return CoachingProgress.model_validate(payload)
        except ValidationError:
            return CoachingProgress()

    def context(
        self,
        *,
        user_id: str,
        course_id: str,
        lecture_id: str,
        gate_id: str,
        gate_title: str,
        now: datetime | None = None,
    ) -> AgentCoachingContext:
        progress = self.read(user_id=user_id, course_id=course_id, lecture_id=lecture_id)
        gate_turns = [turn for turn in progress.turns if turn.gate_id == gate_id]
        transfer = progress.delayed_transfer
        current_time = now or datetime.now(UTC)
        transfer_due = False
        if transfer and transfer.gate_id == gate_id and transfer.completed_at is None:
            try:
                transfer_due = _parse_time(transfer.due_at) <= current_time
            except ValueError:
                transfer_due = False
        return AgentCoachingContext(
            session_goal=progress.session_goal or _default_goal(gate_title),
            goal_is_new=not progress.goal_proposed,
            prior_assistance=bool(gate_turns),
            needs_evidence_count=sum(
                turn.gate_status == QualityGateStatus.NEEDS_EVIDENCE for turn in gate_turns
            ),
            last_gate_status=gate_turns[-1].gate_status.value if gate_turns else None,
            delayed_transfer_due=transfer_due,
        )

    def record_turn(
        self,
        *,
        user_id: str,
        course_id: str,
        lecture_id: str,
        context: AgentCoachingContext,
        policy: TutorScaffoldPolicy,
        decision: QualityGateDecision,
        session_goal: str | None = None,
        now: datetime | None = None,
    ) -> None:
        current_time = now or datetime.now(UTC)
        created_at = current_time.isoformat()
        progress = self.read(user_id=user_id, course_id=course_id, lecture_id=lecture_id)
        progress.session_goal = (session_goal or context.session_goal).strip()
        progress.goal_proposed = True
        progress.turns.append(
            CoachingTurnEvent(
                created_at=created_at,
                gate_id=decision.gate_id,
                gate_status=decision.status,
                support_profile=policy.profile,
                process_label=policy.process_label,
                independent_attempt=(
                    decision.status != QualityGateStatus.NOT_ASSESSED
                    and not context.prior_assistance
                ),
            )
        )
        progress.turns = progress.turns[-MAX_TURN_EVENTS:]
        if decision.status == QualityGateStatus.PASSED:
            progress.delayed_transfer = _updated_transfer(
                progress.delayed_transfer,
                gate_id=decision.gate_id,
                transfer_was_due=context.delayed_transfer_due,
                now=current_time,
            )
        progress.updated_at = created_at
        self._write(
            user_id=user_id,
            course_id=course_id,
            lecture_id=lecture_id,
            progress=progress,
        )

    def _path(self, *, user_id: str, course_id: str, lecture_id: str):
        return self.layout.user_lecture_root(user_id, course_id, lecture_id) / "tutor-state.json"

    def _write(
        self,
        *,
        user_id: str,
        course_id: str,
        lecture_id: str,
        progress: CoachingProgress,
    ) -> None:
        path = self._path(user_id=user_id, course_id=course_id, lecture_id=lecture_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(progress.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def _updated_transfer(
    current: DelayedTransferCheck | None,
    *,
    gate_id: str,
    transfer_was_due: bool,
    now: datetime,
) -> DelayedTransferCheck:
    if current and current.gate_id == gate_id and current.completed_at is None:
        if transfer_was_due:
            return current.model_copy(update={"completed_at": now.isoformat()})
        return current
    return DelayedTransferCheck(gate_id=gate_id, due_at=(now + TRANSFER_DELAY).isoformat())


def _default_goal(gate_title: str) -> str:
    return f"Explain {gate_title} and apply it to one unfamiliar case."


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
