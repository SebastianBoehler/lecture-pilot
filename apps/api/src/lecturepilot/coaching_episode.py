from __future__ import annotations

from datetime import datetime, timedelta

from lecturepilot.coaching_assistance import NextCheck
from lecturepilot.coaching_state_models import (
    AttemptKind,
    CoachingProgress,
    DelayedReview,
    PendingCheck,
    review_key,
)
from lecturepilot.models import AgentCoachingContext, QualityGateDecision


def record_passed_review(
    progress: CoachingProgress,
    *,
    gate_id: str,
    gate_revision: str,
    section_id: str,
    transfer_prompt: str,
    delayed_attempt: bool,
    review_after_days: int,
    now: datetime,
) -> None:
    key = review_key(gate_id, gate_revision)
    current = progress.delayed_reviews.get(key)
    if (
        current is not None
        and current.completed_at is None
        and (delayed_attempt or current.attempted_at is not None)
    ):
        progress.delayed_reviews[key] = current.model_copy(update={"completed_at": now})
        return
    if current is not None:
        return
    planned_seconds = review_after_days * 24 * 60 * 60
    progress.delayed_reviews[key] = DelayedReview(
        gate_id=gate_id,
        gate_revision=gate_revision,
        section_id=section_id,
        transfer_prompt=transfer_prompt,
        scheduled_at=now,
        due_at=now + timedelta(seconds=planned_seconds),
        planned_delay_seconds=planned_seconds,
        attempted_at=None,
        completed_at=None,
        observed_delay_seconds=None,
    )


def record_review_attempt(
    progress: CoachingProgress,
    *,
    gate_id: str,
    gate_revision: str,
    now: datetime,
) -> DelayedReview | None:
    key = review_key(gate_id, gate_revision)
    current = progress.delayed_reviews.get(key)
    if current is None or current.completed_at is not None:
        return None
    observed = int((now - current.scheduled_at).total_seconds())
    if observed < 0:
        raise ValueError("Delayed-review attempt precedes its schedule.")
    updated = current.model_copy(update={"attempted_at": now, "observed_delay_seconds": observed})
    progress.delayed_reviews[key] = updated
    return updated


def pending_from_next_check(
    next_check: NextCheck | None,
    *,
    now: datetime,
) -> PendingCheck | None:
    if next_check is None:
        return None
    return PendingCheck(
        gate_id=next_check.gate_id,
        gate_revision=next_check.gate_revision,
        prompt=next_check.prompt,
        assistance_level=next_check.assistance.level,
        kind="standard",
        issued_at=now,
    )


def bound_pending(
    pending: PendingCheck | None,
    context: AgentCoachingContext,
    decision: QualityGateDecision,
    gate_revision: str,
) -> PendingCheck | None:
    if pending is None or context.pending_check_issued_at != pending.issued_at.isoformat():
        return None
    return pending if matching_pending(pending, decision.gate_id, gate_revision) else None


def matching_pending(
    pending: PendingCheck | None,
    gate_id: str,
    gate_revision: str,
) -> PendingCheck | None:
    if pending is None or pending.gate_id != gate_id or pending.gate_revision != gate_revision:
        return None
    return pending


def attempt_kind(pending: PendingCheck | None, assessed: bool) -> AttemptKind:
    if not assessed or pending is None:
        return "none"
    if pending.kind == "delayed_transfer":
        return "delayed_transfer"
    return "independent" if pending.assistance_level in {"none", "prompt"} else "supported_retry"


def parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("Persisted timestamp requires a timezone.")
    return parsed
