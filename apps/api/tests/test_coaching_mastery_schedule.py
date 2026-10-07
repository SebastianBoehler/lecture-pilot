from datetime import timedelta
from types import SimpleNamespace

from lecturepilot.coaching_goal_evidence import accumulate_goal_evidence
from lecturepilot.coaching_state_models import CoachingProgress
from practice_gate_coaching_test_helpers import NOW, bank_gate


def test_later_independent_failure_clears_current_mastery_but_keeps_supported_evidence():
    gate = bank_gate()
    evidence = {}
    for kind in ["supported_retry", "independent_exit", "delayed_transfer"]:
        accumulate_goal_evidence(
            evidence,
            SimpleNamespace(
                gate_id=gate.id,
                gate_revision=gate.revision,
                gate_status="passed",
                attempt_kind=kind,
                missing_evidence_ids=[],
            ),
        )
    accumulate_goal_evidence(
        evidence,
        SimpleNamespace(
            gate_id=gate.id,
            gate_revision=gate.revision,
            gate_status="needs_evidence",
            attempt_kind="delayed_transfer",
            missing_evidence_ids=["reason"],
        ),
    )
    current = next(iter(evidence.values()))
    assert current.supported
    assert not current.independent and not current.delayed


def test_successful_transfer_schedules_fresh_review_with_expanded_interval():
    from lecturepilot.coaching_episode import schedule_delayed_review, complete_delayed_review

    gate = bank_gate()
    progress = CoachingProgress.empty(course_id="course", lecture_id="lecture")
    schedule_delayed_review(
        progress,
        gate_id=gate.id,
        gate_revision=gate.revision,
        section_id=gate.section_id,
        transfer_prompt=gate.transfer_prompt,
        review_after_days=gate.review_after_days,
        now=NOW,
    )
    key = f"{gate.id}@{gate.revision}"
    review = progress.delayed_reviews[key]
    review.attempted_at = NOW + timedelta(days=gate.review_after_days)
    instant = review.attempted_at + timedelta(minutes=1)
    complete_delayed_review(
        progress,
        gate_id=gate.id,
        gate_revision=gate.revision,
        now=instant,
        gate=gate,
        exposed_task_ids=["delayed-transfer"],
    )
    upcoming = progress.delayed_reviews[key]
    assert upcoming.task_id == "delayed-fresh"
    assert upcoming.due_at == instant + timedelta(days=gate.review_after_days * 2)
    assert upcoming.completed_at is None and upcoming.attempted_at is None
    assert upcoming.last_completed_at == instant


def test_failure_resets_next_interval_and_task_exhaustion_stays_completed():
    from lecturepilot.coaching_review_schedule import advance_review
    from lecturepilot.coaching_state_models import DelayedReview

    gate = bank_gate()
    current = DelayedReview(
        gate_id=gate.id,
        gate_revision=gate.revision,
        section_id=gate.section_id,
        transfer_prompt=gate.transfer_prompt,
        scheduled_at=NOW,
        due_at=NOW + timedelta(days=40),
        planned_delay_seconds=40 * 86400,
        attempted_at=NOW + timedelta(days=40),
        completed_at=None,
        observed_delay_seconds=40 * 86400,
        failed_since_review=True,
    )
    advanced = advance_review(current, gate=gate, exposed_task_ids=["delayed-transfer"], now=NOW)
    assert advanced.due_at == NOW + timedelta(days=gate.review_after_days)
    completed = advance_review(
        current, gate=gate, exposed_task_ids=["delayed-transfer", "delayed-fresh"], now=NOW
    )
    assert completed.completed_at == NOW


def test_review_interval_caps_a_base_interval_above_sixty_days():
    from lecturepilot.coaching_review_schedule import MAX_REVIEW_INTERVAL_DAYS, advance_review
    from lecturepilot.coaching_state_models import DelayedReview
    from lecturepilot.learning_map import LearningMapGate

    gate = bank_gate()
    long_gate = LearningMapGate.create(
        **{**gate.model_dump(exclude={"revision"}), "review_after_days": 90}
    )
    current = DelayedReview(
        gate_id=long_gate.id,
        gate_revision=long_gate.revision,
        section_id=long_gate.section_id,
        transfer_prompt=long_gate.transfer_prompt,
        scheduled_at=NOW,
        due_at=NOW + timedelta(days=40),
        planned_delay_seconds=40 * 86400,
        attempted_at=NOW + timedelta(days=40),
        completed_at=None,
        observed_delay_seconds=40 * 86400,
        failed_since_review=False,
    )
    advanced = advance_review(
        current, gate=long_gate, exposed_task_ids=["delayed-transfer"], now=NOW
    )
    assert advanced.planned_delay_seconds == MAX_REVIEW_INTERVAL_DAYS * 86400


def test_review_queue_interleaves_lectures_and_keeps_each_lecture_in_order():
    from lecturepilot.review_queue_order import interleave_lectures

    items = [
        SimpleNamespace(lecture_id=lecture, id=identity)
        for lecture, identity in [("a", "a1"), ("a", "a2"), ("b", "b1"), ("c", "c1"), ("b", "b2")]
    ]
    assert [item.id for item in interleave_lectures(items)] == ["a1", "b1", "c1", "a2", "b2"]
