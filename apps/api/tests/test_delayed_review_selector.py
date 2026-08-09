from datetime import UTC, datetime

from lecturepilot.coaching_orchestration import select_due_review_gate
from lecturepilot.coaching_state_models import CoachingProgress, DelayedReview
from lecturepilot.learning_map import LearningMap, LearningMapGate


def test_due_review_reactivates_current_gate_contract() -> None:
    gate = LearningMapGate(
        id="gate-1",
        concept_id="concept-1",
        title="Gate 1",
        prompt="Explain gate 1.",
        section_id="section-1",
    )
    learning_map = LearningMap(
        course_id="course-1",
        lecture_id="lecture-1",
        title="Lecture",
        gates=[gate],
    )
    progress = CoachingProgress(
        delayed_reviews={
            "gate-1": DelayedReview(
                gate_id="gate-1",
                gate_revision=gate.revision,
                scheduled_at="2026-07-13T09:00:00+00:00",
                due_at="2026-07-15T09:00:00+00:00",
            )
        }
    )

    selected = select_due_review_gate(
        learning_map,
        progress,
        now=datetime(2026, 7, 16, tzinfo=UTC),
    )

    assert selected == gate
