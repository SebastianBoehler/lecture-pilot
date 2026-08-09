from datetime import UTC, datetime

from lecturepilot.coaching_orchestration import select_due_review_gate
from lecturepilot.coaching_state_models import CoachingProgress, DelayedReview, PendingCheck
from lecturepilot.learning_map import LearningMap, LearningMapGate, LearningMapNode


def test_due_review_reactivates_current_gate_contract() -> None:
    gate = LearningMapGate.create(
        id="gate-1",
        concept_id="concept-1",
        title="Gate 1",
        prompt="Explain gate 1.",
        evidence_criteria=[{"id": "gate-1-evidence", "description": "Explains gate 1."}],
        transfer_prompt="Apply gate 1 to a changed case.",
        review_after_days=2,
        section_id="section-1",
        source_ref=None,
    )
    learning_map = LearningMap.create(
        course_id="course-1",
        lecture_id="lecture-1",
        title="Lecture",
        objective="Explain and apply gate 1.",
        nodes=[
            LearningMapNode(
                id="section-1",
                title="Gate 1",
                lecture_id="lecture-1",
                section_id="section-1",
                source_ref=None,
                prerequisites=[],
                gate_ids=[gate.id],
                quiz_ids=[],
            )
        ],
        gates=[gate],
    )
    progress = CoachingProgress.empty(course_id="course-1", lecture_id="lecture-1")
    key = f"gate-1@{gate.revision}"
    progress.delayed_reviews[key] = DelayedReview(
        gate_id="gate-1",
        gate_revision=gate.revision,
        section_id="section-1",
        transfer_prompt=gate.transfer_prompt,
        scheduled_at=datetime(2026, 7, 13, 9, tzinfo=UTC),
        due_at=datetime(2026, 7, 15, 9, tzinfo=UTC),
        planned_delay_seconds=172800,
        attempted_at=None,
        completed_at=None,
        observed_delay_seconds=None,
    )

    selected = select_due_review_gate(
        learning_map,
        progress,
        now=datetime(2026, 7, 16, tzinfo=UTC),
    )

    assert selected == gate

    progress.delayed_reviews[key] = progress.delayed_reviews[key].model_copy(
        update={"attempted_at": datetime(2026, 7, 16, tzinfo=UTC)}
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
        LearningMapGate.create(
            id=f"gate-{number}",
            concept_id=f"concept-{number}",
            title=f"Gate {number}",
            prompt=f"Explain gate {number}.",
            evidence_criteria=[
                {"id": f"gate-{number}-evidence", "description": f"Explains gate {number}."}
            ],
            transfer_prompt=f"Apply gate {number} to a changed case.",
            review_after_days=2,
            section_id=f"section-{number}",
            source_ref=None,
        )
        for number in (1, 2)
    ]
    learning_map = LearningMap.create(
        course_id="course-1",
        lecture_id="lecture-1",
        title="Lecture",
        objective="Explain and apply both gates.",
        nodes=[
            LearningMapNode(
                id=gate.section_id,
                title=gate.title,
                lecture_id="lecture-1",
                section_id=gate.section_id,
                source_ref=None,
                prerequisites=[],
                gate_ids=[gate.id],
                quiz_ids=[],
            )
            for gate in gates
        ],
        gates=gates,
    )
    progress = CoachingProgress.empty(course_id="course-1", lecture_id="lecture-1")
    progress.pending_check = PendingCheck(
        gate_id="gate-2",
        gate_revision=gates[1].revision,
        prompt="Apply gate 2 to a changed case.",
        assistance_level="none",
        kind="delayed_transfer",
        issued_at=datetime(2026, 7, 16, 8, tzinfo=UTC),
    )
    progress.delayed_reviews = {
        f"{gate.id}@{gate.revision}": DelayedReview(
            gate_id=gate.id,
            gate_revision=gate.revision,
            section_id=gate.section_id,
            transfer_prompt=gate.transfer_prompt,
            scheduled_at=datetime(2026, 7, 13, 9, tzinfo=UTC),
            due_at=datetime(2026, 7, 15, 9, tzinfo=UTC),
            planned_delay_seconds=172800,
            attempted_at=None,
            completed_at=None,
            observed_delay_seconds=None,
        )
        for gate in gates
    }

    selected = select_due_review_gate(
        learning_map,
        progress,
        now=datetime(2026, 7, 16, tzinfo=UTC),
    )

    assert selected == gates[1]
