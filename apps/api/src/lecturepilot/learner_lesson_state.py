from __future__ import annotations

from datetime import UTC, datetime

from lecturepilot.coaching_episode import parse_time
from lecturepilot.coaching_progress import CoachingProgressStore
from lecturepilot.learner_lesson_state_models import (
    LearnerDueGateReview,
    LearnerLessonState,
    LearnerPendingCheck,
)
from lecturepilot.learner_state import LearnerStateStore


def lesson_state_snapshot(
    *,
    learner_store: LearnerStateStore,
    coaching_store: CoachingProgressStore,
    user_id: str,
    course_id: str,
    lecture_id: str,
    publication_version: int,
    now: datetime | None = None,
) -> LearnerLessonState:
    progress = coaching_store.read(
        user_id=user_id,
        course_id=course_id,
        lecture_id=lecture_id,
    )
    decisions = learner_store.latest_gate_decisions(
        user_id=user_id,
        course_id=course_id,
        lecture_id=lecture_id,
    )
    pending = progress.pending_check
    return LearnerLessonState(
        course_id=course_id,
        lecture_id=lecture_id,
        publication_version=publication_version,
        gate_statuses={gate_id: decision.status for gate_id, decision in sorted(decisions.items())},
        quiz_states=learner_store.latest_quiz_states(
            user_id=user_id,
            course_id=course_id,
            lecture_id=lecture_id,
            publication_version=publication_version,
        ),
        active_session_goal=progress.session_goal.strip() or None,
        pending_check=(
            LearnerPendingCheck(
                gate_id=pending.gate_id,
                gate_revision=pending.gate_revision,
                prompt=pending.prompt,
                assistance_level=pending.assistance_level,
                kind=pending.kind,
            )
            if pending
            else None
        ),
        due_gate_reviews=_due_reviews(progress.delayed_reviews.values(), now or datetime.now(UTC)),
    )


def _due_reviews(reviews, now: datetime) -> list[LearnerDueGateReview]:
    due = []
    for review in reviews:
        if review.completed_at is not None or review.attempted_at is not None:
            continue
        try:
            is_due = parse_time(review.due_at) <= now
        except ValueError:
            continue
        if is_due:
            due.append(
                LearnerDueGateReview(
                    gate_id=review.gate_id,
                    gate_revision=review.gate_revision,
                    due_at=review.due_at,
                )
            )
    return sorted(due, key=lambda item: (item.due_at, item.gate_id))
