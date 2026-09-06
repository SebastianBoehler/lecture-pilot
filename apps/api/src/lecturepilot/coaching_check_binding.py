from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from lecturepilot.coaching_task_bank import canonical_task_id, record_task_exposure
from lecturepilot.coaching_episode import matching_pending
from lecturepilot.coaching_state_models import PendingCheck, review_key
from lecturepilot.coaching_transitions import initial_assessment_stage
from lecturepilot.durable_files import exclusive_file_lock
from lecturepilot.learning_map import LearningMapGate

if TYPE_CHECKING:
    from lecturepilot.coaching_progress import CoachingProgressStore


def bind_inline_checkpoint(
    store: CoachingProgressStore,
    *,
    user_id: str,
    course_id: str,
    lecture_id: str,
    gate: LearningMapGate,
    now: datetime | None,
) -> None:
    path = store._path(user_id=user_id, course_id=course_id, lecture_id=lecture_id)
    with exclusive_file_lock(path):
        progress = store.read(user_id=user_id, course_id=course_id, lecture_id=lecture_id)
        current = progress.pending_check
        if current is not None:
            if current.gate_id == gate.id and current.gate_revision == gate.revision:
                return
            raise ValueError("Another assessment is already pending.")
        progress.pending_check = PendingCheck(
            gate_id=gate.id,
            gate_revision=gate.revision,
            prompt=gate.prompt,
            task_id=canonical_task_id(initial_assessment_stage(gate)),
            assistance_level="none",
            assistance_content=None,
            kind="standard",
            stage=initial_assessment_stage(gate),
            issued_at=now or datetime.now(UTC),
        )
        record_task_exposure(progress, progress.pending_check, progress.pending_check.issued_at)
        store._write(
            user_id=user_id,
            course_id=course_id,
            lecture_id=lecture_id,
            progress=progress,
        )


def bind_delayed_review(
    store: CoachingProgressStore,
    *,
    user_id: str,
    course_id: str,
    lecture_id: str,
    gate_id: str,
    gate_revision: str,
    now: datetime | None,
) -> PendingCheck:
    current_time = now or datetime.now(UTC)
    path = store._path(user_id=user_id, course_id=course_id, lecture_id=lecture_id)
    with exclusive_file_lock(path):
        progress = store.read(user_id=user_id, course_id=course_id, lecture_id=lecture_id)
        review = progress.delayed_reviews.get(review_key(gate_id, gate_revision))
        if review is None or review.completed_at is not None:
            raise ValueError("Gate review is no longer available.")
        current = progress.pending_check
        pending = matching_pending(current, gate_id, gate_revision)
        if current is not None and pending is None:
            raise ValueError("Another assessment is already pending.")
        if review.attempted_at is not None:
            if pending is None or pending.stage not in {
                "delayed_support",
                "delayed_transfer",
            }:
                raise ValueError("Gate repair is no longer active.")
            return pending
        if pending is not None:
            if pending.stage in {"delayed_transfer", "delayed_support"}:
                return pending
            raise ValueError("Another assessment is already pending.")
        if review.due_at > current_time:
            raise ValueError("Gate review is not due yet.")
        progress.pending_check = PendingCheck(
            gate_id=gate_id,
            gate_revision=gate_revision,
            prompt=review.transfer_prompt,
            task_id="delayed-transfer",
            assistance_level="none",
            assistance_content=None,
            kind="delayed_transfer",
            stage="delayed_transfer",
            issued_at=current_time,
        )
        record_task_exposure(progress, progress.pending_check, progress.pending_check.issued_at)
        store._write(
            user_id=user_id,
            course_id=course_id,
            lecture_id=lecture_id,
            progress=progress,
        )
        return progress.pending_check
