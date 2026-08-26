from __future__ import annotations

from datetime import UTC, datetime

from pydantic import ValidationError

from lecturepilot.coaching_assistance import NextCheck
from lecturepilot.coaching_check_binding import bind_inline_checkpoint
from lecturepilot.coaching_episode import (
    attempt_kind,
    bound_pending,
    complete_delayed_review,
    matching_pending,
    pending_from_transition,
    record_review_attempt,
    schedule_delayed_review,
)
from lecturepilot.coaching_state_io import MAX_RECENT_MESSAGES, MAX_TURN_EVENTS
from lecturepilot.coaching_state_models import (
    CoachingProgress,
    CoachingTurnEvent,
    HintExposure,
    attempt_key,
    hint_exposure_key,
    review_key,
)
from lecturepilot.coaching_transitions import derive_next_transition
from lecturepilot.durable_files import atomic_write_json, exclusive_file_lock
from lecturepilot.models import AgentCoachingContext, AgentConversationMessage, QualityGateDecision
from lecturepilot.learning_map import LearningMapGate
from lecturepilot.scaffold_policy import TutorScaffoldPolicy
from lecturepilot.storage_layout import StorageLayout


class InvalidCoachingStateError(ValueError):
    pass


class CoachingProgressStore:
    def __init__(self, layout: StorageLayout) -> None:
        self.layout = layout

    def read(self, *, user_id: str, course_id: str, lecture_id: str) -> CoachingProgress:
        path = self._path(user_id=user_id, course_id=course_id, lecture_id=lecture_id)
        if not path.exists():
            return CoachingProgress.empty(course_id=course_id, lecture_id=lecture_id)
        try:
            progress = CoachingProgress.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, ValidationError) as exc:
            raise InvalidCoachingStateError("Persisted tutor state is invalid.") from exc
        if progress.course_id != course_id or progress.lecture_id != lecture_id:
            raise InvalidCoachingStateError("Persisted tutor state is invalid.")
        return progress

    def context(
        self,
        *,
        user_id: str,
        course_id: str,
        lecture_id: str,
        gate_id: str,
        gate_revision: str,
        learning_objective: str,
        now: datetime | None = None,
    ) -> AgentCoachingContext:
        progress = self.read(user_id=user_id, course_id=course_id, lecture_id=lecture_id)
        gate_turns = [
            turn
            for turn in progress.turns
            if turn.gate_id == gate_id and turn.gate_revision == gate_revision
        ]
        latest_turn = gate_turns[-1] if gate_turns else None
        pending = matching_pending(progress.pending_check, gate_id, gate_revision)
        transfer = progress.delayed_reviews.get(review_key(gate_id, gate_revision))
        exposures = sorted(
            (
                exposure
                for exposure in progress.hint_exposures.values()
                if exposure.gate_id == gate_id and exposure.gate_revision == gate_revision
            ),
            key=lambda item: item.exposed_at,
        )
        current_time = now or datetime.now(UTC)
        transfer_due = bool(
            transfer
            and transfer.completed_at is None
            and transfer.attempted_at is None
            and transfer.due_at <= current_time
        )
        return AgentCoachingContext(
            session_goal=progress.session_goal or learning_objective,
            goal_is_new=progress.session_goal is None,
            prior_assistance=bool(gate_turns or pending),
            attendance_prior_used=progress.attendance_prior_used,
            needs_evidence_count=sum(turn.gate_status == "needs_evidence" for turn in gate_turns),
            last_gate_status=latest_turn.gate_status if latest_turn else None,
            delayed_transfer_due=transfer_due,
            support_before_attempt=(pending is not None and pending.assistance_level != "none"),
            last_assistance_level=(pending.assistance_level if pending else "none"),
            pending_check_gate_id=(pending.gate_id if pending else None),
            pending_check_gate_revision=(pending.gate_revision if pending else None),
            pending_check_kind=(pending.kind if pending else None),
            pending_check_stage=(pending.stage if pending else None),
            pending_check_issued_at=(pending.issued_at.isoformat() if pending else None),
            pending_check_prompt=(pending.prompt if pending else None),
            pending_check_assistance_content=(pending.assistance_content if pending else None),
            exposed_hint_levels=[item.assistance_level for item in exposures],
            delayed_review_attempted=bool(transfer and transfer.attempted_at is not None),
            evidence_ids=sorted({item for turn in gate_turns for item in turn.evidence_ids}),
            missing_evidence_ids=(latest_turn.missing_evidence_ids if latest_turn else []),
        )

    def bind_inline_checkpoint(
        self,
        *,
        user_id: str,
        course_id: str,
        lecture_id: str,
        gate: LearningMapGate,
        now: datetime | None = None,
    ) -> None:
        bind_inline_checkpoint(
            self,
            user_id=user_id,
            course_id=course_id,
            lecture_id=lecture_id,
            gate=gate,
            now=now,
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
        next_check: NextCheck | None,
        gate: LearningMapGate,
        user_message: str,
        assistant_message: str,
        session_goal: str | None = None,
        now: datetime | None = None,
    ) -> CoachingTurnEvent:
        current_time = now or datetime.now(UTC)
        path = self._path(user_id=user_id, course_id=course_id, lecture_id=lecture_id)
        with exclusive_file_lock(path):
            progress = self.read(user_id=user_id, course_id=course_id, lecture_id=lecture_id)
            pending = bound_pending(
                progress.pending_check, context, decision, decision.gate_revision
            )
            if pending is None:
                raise ValueError("Assessment is not bound to the persisted pending check.")
            kind = attempt_kind(pending, True)
            if kind == "none":
                raise ValueError("Assessment requires an attempt kind.")
            timing = (
                record_review_attempt(
                    progress,
                    gate_id=decision.gate_id,
                    gate_revision=decision.gate_revision,
                    now=current_time,
                )
                if kind == "delayed_transfer"
                else None
            )
            count_key = attempt_key(decision.gate_id, decision.gate_revision, kind)
            attempt_index = progress.attempt_counts.get(count_key, 0) + 1
            progress.attempt_counts[count_key] = attempt_index
            event = CoachingTurnEvent(
                created_at=current_time,
                gate_id=decision.gate_id,
                gate_revision=decision.gate_revision,
                gate_status=decision.status.value,
                support_profile=policy.profile,
                process_label=policy.process_label,
                attempt_kind=kind,
                attempt_index=attempt_index,
                assistance_level=pending.assistance_level,
                planned_delay_seconds=(timing.planned_delay_seconds if timing else None),
                observed_delay_seconds=(timing.observed_delay_seconds if timing else None),
                evidence_ids=decision.evidence_ids,
                missing_evidence_ids=decision.missing_evidence_ids,
            )
            progress.turns = [*progress.turns, event][-MAX_TURN_EVENTS:]
            transition = derive_next_transition(
                gate,
                current_stage=pending.stage,
                status=decision.status,
                exposed_hint_levels=[
                    item.assistance_level
                    for item in progress.hint_exposures.values()
                    if item.gate_id == gate.id and item.gate_revision == gate.revision
                ],
            )
            expected_check = transition.check if transition else None
            if next_check != expected_check:
                raise ValueError("Tutor response substituted the server-selected next check.")
            if decision.status.value == "passed" and kind == "independent_exit":
                schedule_delayed_review(
                    progress,
                    gate_id=decision.gate_id,
                    gate_revision=decision.gate_revision,
                    section_id=gate.section_id,
                    transfer_prompt=gate.transfer_prompt,
                    review_after_days=gate.review_after_days,
                    now=current_time,
                )
            elif decision.status.value == "passed" and kind == "delayed_transfer":
                complete_delayed_review(
                    progress,
                    gate_id=decision.gate_id,
                    gate_revision=decision.gate_revision,
                    now=current_time,
                )
            if transition is not None and transition.check.assistance.level != "none":
                assistance = transition.check.assistance
                key = hint_exposure_key(gate.revision, assistance.level)
                progress.hint_exposures[key] = HintExposure(
                    gate_id=gate.id,
                    gate_revision=gate.revision,
                    assistance_level=assistance.level,
                    content=assistance.content or "",
                    exposed_at=current_time,
                )
            progress.pending_check = pending_from_transition(transition, now=current_time)
            progress.session_goal = session_goal.strip() if session_goal else progress.session_goal
            progress.attendance_prior_used = True
            self._append_exchange(progress, user_message, assistant_message)
            progress.updated_at = current_time
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
        next_check: NextCheck | None = None,
        session_goal: str | None = None,
        now: datetime | None = None,
    ) -> None:
        path = self._path(user_id=user_id, course_id=course_id, lecture_id=lecture_id)
        with exclusive_file_lock(path):
            progress = self.read(user_id=user_id, course_id=course_id, lecture_id=lecture_id)
            progress.session_goal = session_goal.strip() if session_goal else progress.session_goal
            progress.attendance_prior_used = True
            if next_check is not None:
                raise ValueError("An unassessed turn cannot create a pending check.")
            self._append_exchange(progress, user_message, assistant_message)
            progress.updated_at = now or datetime.now(UTC)
            self._write(
                user_id=user_id,
                course_id=course_id,
                lecture_id=lecture_id,
                progress=progress,
            )

    def _append_exchange(
        self, progress: CoachingProgress, user_message: str, assistant_message: str
    ) -> None:
        progress.messages.extend(
            [
                AgentConversationMessage(role="user", content=user_message),
                AgentConversationMessage(role="assistant", content=assistant_message),
            ]
        )
        progress.messages = progress.messages[-MAX_RECENT_MESSAGES:]

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
        validated = CoachingProgress.model_validate(progress)
        atomic_write_json(path, validated.model_dump(mode="json"))
