from datetime import UTC, datetime

from lecturepilot.coaching_orchestration import select_due_review_gate
from lecturepilot.coaching_state_models import CoachingProgress, DelayedReview, PendingCheck
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

    progress.delayed_reviews["gate-1"] = progress.delayed_reviews["gate-1"].model_copy(
        update={"attempted_at": "2026-07-16T00:00:00+00:00"}
    )
    assert (
        select_due_review_gate(
            learning_map,
            progress,
            now=datetime(2026, 7, 16, tzinfo=UTC),
        )
        is None
    )


def test_opened_due_review_target_wins_when_multiple_gates_are_due() -> None:
    gates = [
        LearningMapGate(
            id=f"gate-{number}",
            concept_id=f"concept-{number}",
            title=f"Gate {number}",
            prompt=f"Explain gate {number}.",
            transfer_prompt=f"Apply gate {number} to a changed case.",
            section_id=f"section-{number}",
        )
        for number in (1, 2)
    ]
    learning_map = LearningMap(
        course_id="course-1",
        lecture_id="lecture-1",
        title="Lecture",
        gates=gates,
    )
    progress = CoachingProgress(
        pending_check=PendingCheck(
            gate_id="gate-2",
            gate_revision=gates[1].revision,
            prompt="Apply gate 2 to a changed case.",
            assistance_level="none",
            kind="delayed_transfer",
            issued_at="2026-07-16T08:00:00+00:00",
        ),
        delayed_reviews={
            gate.id: DelayedReview(
                gate_id=gate.id,
                gate_revision=gate.revision,
                due_at="2026-07-15T09:00:00+00:00",
            )
            for gate in gates
        },
    )

    selected = select_due_review_gate(
        learning_map,
        progress,
        now=datetime(2026, 7, 16, tzinfo=UTC),
    )

    assert selected == gates[1]
