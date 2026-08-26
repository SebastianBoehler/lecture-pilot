from datetime import timedelta

from auth_helpers import student_headers
from lecturepilot.coaching_assistance import NextCheck, NextCheckAssistance
from lecturepilot.coaching_check_binding import bind_delayed_review
from lecturepilot.coaching_progress import CoachingProgressStore
from lecturepilot.course_learning_design_models import LearningDesignGateInput
from lecturepilot.learner_lesson_state import lesson_state_snapshot
from lecturepilot.learner_state import LearnerStateStore
from lecturepilot.models import QualityGateDecision, QualityGateStatus
from lecturepilot.review_queue_models import GateReviewOpening
from lecturepilot.scaffold_policy import scaffold_policy_for_assessment_stage
from lecturepilot.storage_layout import StorageLayout
from practice_gate_coaching_test_helpers import IDS, NOW, practice_gate
from review_queue_test_helpers import (
    COURSE_ID as REVIEW_COURSE_ID,
    review_client,
    write_review,
)


def test_exact_two_thousand_character_baseline_survives_binding_and_hydration(
    tmp_path,
) -> None:
    baseline = "b" * 2_000
    layout = StorageLayout(tmp_path)
    store = CoachingProgressStore(layout)
    gate = practice_gate(baseline_task=baseline)
    edited_gate = LearningDesignGateInput(
        id=gate.id,
        prompt=baseline,
        evidence_criteria=gate.evidence_criteria,
        transfer_prompt=gate.transfer_prompt,
        review_after_days=gate.review_after_days,
    )

    store.bind_inline_checkpoint(**IDS, gate=gate, now=NOW)
    state = lesson_state_snapshot(
        learner_store=LearnerStateStore(layout),
        coaching_store=store,
        **IDS,
        publication_version=1,
        now=NOW,
    )

    assert gate.prompt == baseline
    assert edited_gate.prompt == baseline
    assert state.pending_check is not None
    assert state.pending_check.prompt == baseline


def test_exact_two_thousand_character_delayed_transfer_survives_review_flow(
    tmp_path,
) -> None:
    transfer = "t" * 2_000
    store = CoachingProgressStore(StorageLayout(tmp_path))
    gate = practice_gate(delayed_transfer_task=transfer)
    edited_gate = LearningDesignGateInput(
        id=gate.id,
        prompt=gate.prompt,
        evidence_criteria=gate.evidence_criteria,
        transfer_prompt=transfer,
        review_after_days=gate.review_after_days,
    )
    store.bind_inline_checkpoint(**IDS, gate=gate, now=NOW)
    _record_pass(
        store,
        gate,
        next_check=NextCheck(
            gate_id=gate.id,
            gate_revision=gate.revision,
            prompt=gate.independent_exit_task,
            assistance=NextCheckAssistance(level="none", content=None),
        ),
        now=NOW + timedelta(minutes=1),
    )
    _record_pass(store, gate, next_check=None, now=NOW + timedelta(minutes=2))

    due = NOW + timedelta(days=gate.review_after_days, minutes=2)
    pending = bind_delayed_review(
        store,
        **IDS,
        gate_id=gate.id,
        gate_revision=gate.revision,
        now=due,
    )
    opening = GateReviewOpening(
        course_id=IDS["course_id"],
        lecture_id=IDS["lecture_id"],
        section_id=gate.section_id,
        gate_id=gate.id,
        gate_revision=gate.revision,
        prompt=pending.prompt,
        stage="due",
    )

    [review] = store.read(**IDS).delayed_reviews.values()
    assert review.transfer_prompt == transfer
    assert edited_gate.transfer_prompt == transfer
    assert pending.prompt == transfer
    assert opening.prompt == transfer


def test_exact_two_thousand_character_tasks_survive_published_api_round_trip(
    tmp_path,
) -> None:
    baseline = _exact_task("Explain the causal boundary in this canonical scenario.", " baseline")
    transfer = _exact_task("Apply the same boundary in this changed scenario.", " transfer")
    client = review_client(
        tmp_path,
        baseline_prompt=baseline,
        delayed_transfer_prompt=transfer,
    )
    headers = student_headers("student-a", course_ids=[REVIEW_COURSE_ID])
    map_response = client.get(
        f"/courses/{REVIEW_COURSE_ID}/lectures/lecture-a/learning-map",
        headers=headers,
    )
    assert map_response.status_code == 200
    gate_id = "practice-practice-target"
    gate = next(item for item in map_response.json()["gates"] if item["id"] == gate_id)
    assert gate["prompt"] == baseline
    assert gate["transfer_prompt"] == transfer
    write_review(client, "student-a", "lecture-a", gate_id, NOW - timedelta(days=1))

    opened = client.post(
        f"/courses/{REVIEW_COURSE_ID}/review-queue/gates/lecture-a/{gate_id}/open",
        headers=headers,
    )

    assert opened.status_code == 200
    assert opened.json()["prompt"] == transfer
    assert len(opened.json()["prompt"]) == 2_000


def _record_pass(store, gate, *, next_check, now) -> None:
    context = store.context(
        **IDS,
        gate_id=gate.id,
        gate_revision=gate.revision,
        learning_objective="Apply the invariant independently.",
        now=now,
    )
    store.record_turn(
        **IDS,
        context=context,
        policy=scaffold_policy_for_assessment_stage(
            stage=context.pending_check_stage,
            assistance_level=context.last_assistance_level,
        ),
        decision=QualityGateDecision(
            gate_id=gate.id,
            gate_revision=gate.revision,
            status=QualityGateStatus.PASSED,
            reason="Server-owned assessment.",
            evidence_ids=[item.id for item in gate.evidence_criteria],
            missing_evidence_ids=[],
        ),
        next_check=next_check,
        gate=gate,
        user_message="Learner attempt.",
        assistant_message="Server-owned assessment.",
        now=now,
    )


def _exact_task(prefix: str, padding: str) -> str:
    repeated = padding * 2_000
    task = (prefix + repeated)[:2_000]
    return task[:-1] + "x" if task[-1].isspace() else task
