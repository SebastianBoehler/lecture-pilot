from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from lecturepilot.coaching_episode import matching_pending, parse_time
from lecturepilot.coaching_state_models import PendingCheck
from lecturepilot.durable_files import exclusive_file_lock

if TYPE_CHECKING:
    from lecturepilot.coaching_progress import CoachingProgressStore


def bind_inline_checkpoint(
    store: CoachingProgressStore,
    *,
    user_id: str,
    course_id: str,
    lecture_id: str,
    gate_id: str,
    gate_revision: str | None,
    published_prompt: str,
    now: datetime | None,
) -> None:
    path = store._path(user_id=user_id, course_id=course_id, lecture_id=lecture_id)
    with exclusive_file_lock(path):
        progress = store.read(user_id=user_id, course_id=course_id, lecture_id=lecture_id)
        progress.pending_check = PendingCheck(
            gate_id=gate_id,
            gate_revision=gate_revision,
            prompt=published_prompt,
            assistance_level="none",
            kind="standard",
            issued_at=(now or datetime.now(UTC)).isoformat(),
        )
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
    transfer_prompt: str,
    now: datetime | None,
) -> PendingCheck:
    current_time = now or datetime.now(UTC)
    path = store._path(user_id=user_id, course_id=course_id, lecture_id=lecture_id)
    with exclusive_file_lock(path):
        progress = store.read(user_id=user_id, course_id=course_id, lecture_id=lecture_id)
        review = progress.delayed_reviews.get(gate_id)
        if review is None or review.completed_at is not None:
            raise ValueError("Gate review is no longer available.")
        if review.gate_revision != gate_revision:
            raise ValueError("Gate review does not match the current publication.")
        if review.attempted_at is not None:
            pending = matching_pending(progress.pending_check, gate_id, gate_revision)
            if pending is None or pending.kind != "standard":
                raise ValueError("Gate repair is no longer active.")
            return pending
        try:
            due_at = parse_time(review.due_at)
        except ValueError as exc:
            raise ValueError("Gate review due time is invalid.") from exc
        if due_at > current_time:
            raise ValueError("Gate review is not due yet.")
        progress.pending_check = PendingCheck(
            gate_id=gate_id,
            gate_revision=gate_revision,
            prompt=transfer_prompt.strip(),
            assistance_level="none",
            kind="delayed_transfer",
            issued_at=current_time.isoformat(),
        )
        store._write(
            user_id=user_id,
            course_id=course_id,
            lecture_id=lecture_id,
            progress=progress,
        )
        return progress.pending_check
