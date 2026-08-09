from __future__ import annotations

from datetime import UTC, datetime, timedelta

from lecturepilot.coaching_state_models import (
    AttemptKind,
    CoachingProgress,
    DelayedReview,
    PendingCheck,
)
from lecturepilot.models import AgentCoachingContext, QualityGateDecision
from lecturepilot.scaffold_policy import AssistanceLevel


def record_passed_review(
    progress: CoachingProgress,
    *,
    gate_id: str,
    gate_revision: str | None,
    delayed_attempt: bool,
    review_after_days: int,
    now: datetime,
) -> None:
    current = progress.delayed_reviews.get(gate_id)
    same_revision = current is not None and current.gate_revision == gate_revision
    if delayed_attempt and current and same_revision and current.completed_at is None:
        progress.delayed_reviews[gate_id] = current.model_copy(
            update={"completed_at": now.isoformat()}
        )
        return
    if current and same_revision and current.completed_at is None:
        return
    progress.delayed_reviews[gate_id] = DelayedReview(
        gate_id=gate_id,
        gate_revision=gate_revision,
        scheduled_at=now.isoformat(),
        due_at=(now + timedelta(days=review_after_days)).isoformat(),
    )


def next_pending_check(
    decision: QualityGateDecision,
    *,
    gate_revision: str | None,
    assistance_level: AssistanceLevel,
    delayed_transfer_due: bool,
    now: datetime,
) -> PendingCheck | None:
    if not decision.next_prompt or not decision.next_prompt.strip():
        return None
    return PendingCheck(
        gate_id=decision.gate_id,
        gate_revision=gate_revision,
        prompt=decision.next_prompt.strip(),
        assistance_level=assistance_level,
        kind="delayed_transfer" if delayed_transfer_due else "standard",
        issued_at=now.isoformat(),
    )


def bound_pending(
    pending: PendingCheck | None,
    context: AgentCoachingContext,
    decision: QualityGateDecision,
    gate_revision: str | None,
) -> PendingCheck | None:
    if pending is None or context.pending_check_issued_at != pending.issued_at:
        return None
    return pending if matching_pending(pending, decision.gate_id, gate_revision) else None


def matching_pending(
    pending: PendingCheck | None,
    gate_id: str,
    gate_revision: str | None,
) -> PendingCheck | None:
    if pending is None or pending.gate_id != gate_id:
        return None
    return pending if revision_matches(pending.gate_revision, gate_revision) else None


def revision_matches(stored: str | None, active: str | None) -> bool:
    return stored == active


def attempt_kind(pending: PendingCheck | None, assessed: bool) -> AttemptKind:
    if not assessed or pending is None:
        return "none"
    if pending.kind == "delayed_transfer":
        return "delayed_transfer"
    return "independent" if pending.assistance_level in {"none", "prompt"} else "supported_retry"


def delay_seconds(review: DelayedReview | None, now: datetime) -> int | None:
    if review is None or review.scheduled_at is None:
        return None
    try:
        return max(0, int((now - parse_time(review.scheduled_at)).total_seconds()))
    except ValueError:
        return None


def parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
