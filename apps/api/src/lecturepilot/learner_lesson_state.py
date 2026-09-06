from __future__ import annotations

from datetime import UTC, datetime

from lecturepilot.coaching_goal_evidence import accumulate_goal_evidence
from lecturepilot.coaching_task_bank import canonical_task_id
from lecturepilot.coaching_progress import CoachingProgressStore
from lecturepilot.coaching_state_models import CoachingProgress
from lecturepilot.learner_lesson_state_models import (
    LearnerDueGateReview,
    LearnerGoalEvidence,
    LearnerLessonState,
    LearnerPendingCheck,
)
from lecturepilot.learning_map import LearningMap
from lecturepilot.learner_state import LearnerStateStore


def lesson_state_snapshot(
    *,
    learner_store: LearnerStateStore,
    coaching_store: CoachingProgressStore,
    user_id: str,
    course_id: str,
    lecture_id: str,
    publication_version: int,
    learning_map: LearningMap,
    progress: CoachingProgress | None = None,
    now: datetime | None = None,
) -> LearnerLessonState:
    if progress is None:
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
        active_session_goal=(progress.session_goal.strip() if progress.session_goal else None),
        pending_check=(
            LearnerPendingCheck(
                gate_id=pending.gate_id,
                gate_revision=pending.gate_revision,
                prompt=pending.prompt,
                assistance_level=pending.assistance_level,
                kind=pending.kind,
                task_id=pending.task_id or canonical_task_id(pending.stage),
                stage=pending.stage,
                issued_at=pending.issued_at.isoformat(),
                assistance_content=pending.assistance_content,
                focus_required=pending.stage in {"independent_exit", "delayed_transfer"},
                bank_exhausted=pending.bank_exhausted,
            )
            if pending
            else None
        ),
        goal_evidence=_goal_evidence(progress, learning_map.gates),
        due_gate_reviews=_due_reviews(progress.delayed_reviews.values(), now or datetime.now(UTC)),
    )


def _due_reviews(reviews, now: datetime) -> list[LearnerDueGateReview]:
    due = []
    for review in reviews:
        if review.completed_at is not None or review.attempted_at is not None:
            continue
        if review.due_at <= now:
            due.append(
                LearnerDueGateReview(
                    gate_id=review.gate_id,
                    gate_revision=review.gate_revision,
                    due_at=review.due_at,
                )
            )
    return sorted(due, key=lambda item: (item.due_at, item.gate_id))


def _goal_evidence(progress, gates):
    focused = progress.pending_check is not None and progress.pending_check.stage in {
        "independent_exit",
        "delayed_transfer",
    }
    evidence = {key: value.model_copy(deep=True) for key, value in progress.goal_evidence.items()}
    if not evidence:
        for turn in progress.turns:
            accumulate_goal_evidence(evidence, turn)
    result = []
    for gate in gates:
        item = evidence.get(f"{gate.id}@{gate.revision}")
        missing = item.missing_evidence_ids if item and not focused else []
        payload = (
            item.model_dump()
            if item
            else dict(gate_id=gate.id, gate_revision=gate.revision, missing_evidence_ids=missing)
        )
        payload["missing_evidence_ids"] = missing
        result.append(
            LearnerGoalEvidence(
                **payload,
                missing_evidence=[
                    criterion.description
                    for criterion in gate.evidence_criteria
                    if criterion.id in missing
                ],
            )
        )
    return result
