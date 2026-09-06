from __future__ import annotations

from datetime import UTC, datetime


from lecturepilot.coaching_goal_evidence import accumulate_goal_evidence
from lecturepilot.coaching_task_bank import canonical_task_id, exposed_ids, record_task_exposure
from lecturepilot.coaching_assistance import NextCheck
from lecturepilot.coaching_episode import (
    attempt_kind,
    bound_pending,
    complete_delayed_review,
    pending_from_transition,
    record_review_attempt,
    schedule_delayed_review,
)
from lecturepilot.coaching_state_io import MAX_TURN_EVENTS
from lecturepilot.coaching_state_models import (
    CoachingTurnEvent,
    HintExposure,
    attempt_key,
    hint_exposure_key,
)
from lecturepilot.coaching_transitions import derive_next_transition
from lecturepilot.durable_files import exclusive_file_lock
from lecturepilot.models import AgentCoachingContext, QualityGateDecision
from lecturepilot.learning_map import LearningMapGate
from lecturepilot.scaffold_policy import TutorScaffoldPolicy


def record_coaching_turn(
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
        pending = bound_pending(progress.pending_check, context, decision, decision.gate_revision)
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
            task_id=pending.task_id or canonical_task_id(pending.stage),
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
        if not progress.goal_evidence:
            for prior in progress.turns:
                accumulate_goal_evidence(progress.goal_evidence, prior)
        accumulate_goal_evidence(progress.goal_evidence, event)
        progress.turns = [*progress.turns, event][-MAX_TURN_EVENTS:]
        transition = derive_next_transition(
            gate,
            current_stage=pending.stage,
            current_task_id=pending.task_id,
            exposed_task_ids=exposed_ids(progress, gate.id, gate.revision),
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
        record_task_exposure(progress, pending, current_time, answered=True)
        progress.pending_check = pending_from_transition(transition, now=current_time)
        if progress.pending_check is not None:
            record_task_exposure(progress, progress.pending_check, current_time)
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
