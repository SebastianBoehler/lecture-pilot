from __future__ import annotations

import json
from datetime import UTC, datetime

from pydantic import ValidationError

from lecturepilot.coaching_state_models import (
    CoachingProgress,
    CoachingTurnEvent,
    PendingCheck,
)
from lecturepilot.coaching_episode import (
    attempt_kind,
    bound_pending,
    delay_seconds,
    matching_pending,
    next_pending_check,
    parse_time,
    record_passed_review,
    record_review_attempt,
    revision_matches,
)
from lecturepilot.coaching_state_io import (
    MAX_RECENT_MESSAGES,
    MAX_TURN_EVENTS,
    migrate_coaching_payload,
)
from lecturepilot.durable_files import atomic_write_json, exclusive_file_lock
from lecturepilot.models import (
    AgentCoachingContext,
    AgentConversationMessage,
    QualityGateDecision,
    QualityGateStatus,
)
from lecturepilot.scaffold_policy import AssistanceLevel, TutorScaffoldPolicy
from lecturepilot.storage_layout import StorageLayout


class CoachingProgressStore:
    def __init__(self, layout: StorageLayout) -> None:
        self.layout = layout

    def read(self, *, user_id: str, course_id: str, lecture_id: str) -> CoachingProgress:
        path = self._path(user_id=user_id, course_id=course_id, lecture_id=lecture_id)
        if not path.exists():
            return CoachingProgress()
        try:
            payload = migrate_coaching_payload(json.loads(path.read_text(encoding="utf-8")))
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
        gate_revision: str | None = None,
        now: datetime | None = None,
    ) -> AgentCoachingContext:
        progress = self.read(user_id=user_id, course_id=course_id, lecture_id=lecture_id)
        gate_turns = [turn for turn in progress.turns if turn.gate_id == gate_id]
        attempt_turns = [turn for turn in gate_turns if turn.attempt_kind != "none"]
        latest_turn = attempt_turns[-1] if attempt_turns else None
        pending = matching_pending(progress.pending_check, gate_id, gate_revision)
        transfer = progress.delayed_reviews.get(gate_id)
        current_time = now or datetime.now(UTC)
        transfer_due = False
        if (
            transfer
            and transfer.completed_at is None
            and transfer.attempted_at is None
            and revision_matches(transfer.gate_revision, gate_revision)
        ):
            try:
                transfer_due = parse_time(transfer.due_at) <= current_time
            except ValueError:
                transfer_due = False
        return AgentCoachingContext(
            session_goal=progress.session_goal or _default_goal(gate_title),
            goal_is_new=not progress.goal_proposed,
            prior_assistance=bool(gate_turns or pending),
            attendance_prior_used=progress.attendance_prior_used,
            needs_evidence_count=sum(
                turn.gate_status == QualityGateStatus.NEEDS_EVIDENCE for turn in attempt_turns
            ),
            last_gate_status=latest_turn.gate_status.value if latest_turn else None,
            delayed_transfer_due=transfer_due,
            support_before_attempt=(pending is not None and pending.assistance_level != "none"),
            last_assistance_level=(pending.assistance_level if pending else "none"),
            pending_check_gate_id=(pending.gate_id if pending else None),
            pending_check_gate_revision=(pending.gate_revision if pending else None),
            pending_check_kind=(pending.kind if pending else None),
            pending_check_issued_at=(pending.issued_at if pending else None),
            pending_check_prompt=(pending.prompt if pending else None),
            evidence_ids=sorted(
                {evidence_id for turn in attempt_turns for evidence_id in turn.evidence_ids}
            ),
            missing_evidence_ids=(latest_turn.missing_evidence_ids if latest_turn else []),
        )

    def bind_inline_checkpoint(
        self,
        *,
        user_id: str,
        course_id: str,
        lecture_id: str,
        gate_id: str,
        gate_revision: str | None,
        published_prompt: str,
        now: datetime | None = None,
    ) -> None:
        path = self._path(user_id=user_id, course_id=course_id, lecture_id=lecture_id)
        with exclusive_file_lock(path):
            progress = self.read(user_id=user_id, course_id=course_id, lecture_id=lecture_id)
            progress.pending_check = PendingCheck(
                gate_id=gate_id,
                gate_revision=gate_revision,
                prompt=published_prompt,
                assistance_level="none",
                kind="standard",
                issued_at=(now or datetime.now(UTC)).isoformat(),
            )
            self._write(
                user_id=user_id,
                course_id=course_id,
                lecture_id=lecture_id,
                progress=progress,
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
        gate_revision: str | None = None,
        user_message: str | None = None,
        assistant_message: str | None = None,
        session_goal: str | None = None,
        next_check_assistance_level: AssistanceLevel = "none",
        review_after_days: int = 2,
        now: datetime | None = None,
    ) -> CoachingTurnEvent:
        current_time = now or datetime.now(UTC)
        created_at = current_time.isoformat()
        path = self._path(user_id=user_id, course_id=course_id, lecture_id=lecture_id)
        with exclusive_file_lock(path):
            progress = self.read(user_id=user_id, course_id=course_id, lecture_id=lecture_id)
            progress.session_goal = (session_goal or context.session_goal).strip()
            progress.goal_proposed = True
            progress.attendance_prior_used = True
            pending = bound_pending(progress.pending_check, context, decision, gate_revision)
            assessed_attempt = (
                pending is not None and decision.status != QualityGateStatus.NOT_ASSESSED
            )
            event_attempt_kind = attempt_kind(pending, assessed_attempt)
            attempt_index = (
                progress.attempt_counts.get(decision.gate_id, 0) + 1 if assessed_attempt else None
            )
            if attempt_index is not None:
                progress.attempt_counts[decision.gate_id] = attempt_index
            assistance_level = pending.assistance_level if assessed_attempt and pending else "none"
            observed_delay_seconds = (
                delay_seconds(progress.delayed_reviews.get(decision.gate_id), current_time)
                if event_attempt_kind == "delayed_transfer"
                else None
            )
            event = CoachingTurnEvent(
                created_at=created_at,
                gate_id=decision.gate_id,
                gate_revision=gate_revision,
                gate_status=decision.status,
                support_profile=policy.profile,
                process_label=policy.process_label,
                attempt_kind=event_attempt_kind,
                attempt_index=attempt_index,
                assistance_level=assistance_level,
                delay_seconds=observed_delay_seconds,
                independent_attempt=event_attempt_kind == "independent",
                support_before_attempt=event_attempt_kind == "supported_retry",
                transfer_attempt=event_attempt_kind == "delayed_transfer",
                evidence_ids=decision.evidence_ids,
                missing_evidence_ids=decision.missing_evidence_ids,
            )
            progress.turns.append(event)
            progress.turns = progress.turns[-MAX_TURN_EVENTS:]
            if event_attempt_kind == "delayed_transfer":
                record_review_attempt(
                    progress,
                    gate_id=decision.gate_id,
                    gate_revision=gate_revision,
                    now=current_time,
                )
            if assessed_attempt and decision.status == QualityGateStatus.PASSED:
                record_passed_review(
                    progress,
                    gate_id=decision.gate_id,
                    gate_revision=gate_revision,
                    delayed_attempt=event_attempt_kind == "delayed_transfer",
                    review_after_days=review_after_days,
                    now=current_time,
                )
            progress.pending_check = next_pending_check(
                decision,
                gate_revision=gate_revision,
                assistance_level=next_check_assistance_level,
                delayed_transfer_due=(
                    context.delayed_transfer_due and event_attempt_kind == "none"
                ),
                now=current_time,
            )
            if user_message and assistant_message:
                progress.messages.extend(
                    [
                        AgentConversationMessage(role="user", content=user_message),
                        AgentConversationMessage(role="assistant", content=assistant_message),
                    ]
                )
                progress.messages = progress.messages[-MAX_RECENT_MESSAGES:]
            progress.updated_at = created_at
            self._write(
                user_id=user_id,
                course_id=course_id,
                lecture_id=lecture_id,
                progress=progress,
            )
            return event

    def record_exchange(
        self,
        *,
        user_id: str,
        course_id: str,
        lecture_id: str,
        user_message: str,
        assistant_message: str,
        session_goal: str | None = None,
        now: datetime | None = None,
    ) -> None:
        path = self._path(user_id=user_id, course_id=course_id, lecture_id=lecture_id)
        with exclusive_file_lock(path):
            progress = self.read(user_id=user_id, course_id=course_id, lecture_id=lecture_id)
            if session_goal:
                progress.session_goal = session_goal.strip()
                progress.goal_proposed = True
            progress.attendance_prior_used = True
            progress.messages.extend(
                [
                    AgentConversationMessage(role="user", content=user_message),
                    AgentConversationMessage(role="assistant", content=assistant_message),
                ]
            )
            progress.messages = progress.messages[-MAX_RECENT_MESSAGES:]
            progress.updated_at = (now or datetime.now(UTC)).isoformat()
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
        atomic_write_json(path, progress.model_dump(mode="json"))


def _default_goal(gate_title: str) -> str:
    return f"Explain {gate_title} and apply it to one unfamiliar case."
