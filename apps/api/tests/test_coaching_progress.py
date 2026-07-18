from datetime import UTC, datetime, timedelta

from lecturepilot.coaching_progress import CoachingProgressStore
from lecturepilot.models import (
    AgentCoachingContext,
    QualityGateDecision,
    QualityGateStatus,
)
from lecturepilot.scaffold_policy import scaffold_policy_for_tutor_turn
from lecturepilot.storage_layout import StorageLayout


def test_first_assessed_turn_is_recorded_as_independent_attempt(tmp_path) -> None:
    store = CoachingProgressStore(StorageLayout(tmp_path))
    context = store.context(
        user_id="student-1",
        course_id="course-1",
        lecture_id="lecture-1",
        gate_id="gate-1",
        gate_title="Model selection",
    )
    policy = _policy(context)

    store.record_turn(
        user_id="student-1",
        course_id="course-1",
        lecture_id="lecture-1",
        context=context,
        policy=policy,
        decision=_decision(QualityGateStatus.NEEDS_EVIDENCE),
    )

    progress = store.read(user_id="student-1", course_id="course-1", lecture_id="lecture-1")
    assert context.goal_is_new is True
    assert progress.session_goal == "Explain Model selection and apply it to one unfamiliar case."
    assert progress.turns[0].independent_attempt is True
    assert progress.turns[0].support_profile == "self_explanation"
    assert progress.turns[0].support_before_attempt is False
    assert progress.turns[0].assistance_level == "prompt"


def test_prior_tutor_turn_prevents_assisted_answer_from_counting_as_independent(tmp_path) -> None:
    store = CoachingProgressStore(StorageLayout(tmp_path))
    first = store.context(
        user_id="student-1",
        course_id="course-1",
        lecture_id="lecture-1",
        gate_id="gate-1",
        gate_title="Model selection",
    )
    store.record_turn(
        user_id="student-1",
        course_id="course-1",
        lecture_id="lecture-1",
        context=first,
        policy=_policy(first),
        decision=_decision(QualityGateStatus.NOT_ASSESSED),
    )
    second = store.context(
        user_id="student-1",
        course_id="course-1",
        lecture_id="lecture-1",
        gate_id="gate-1",
        gate_title="Model selection",
    )

    store.record_turn(
        user_id="student-1",
        course_id="course-1",
        lecture_id="lecture-1",
        context=second,
        policy=_policy(second),
        decision=_decision(QualityGateStatus.PASSED),
    )

    progress = store.read(user_id="student-1", course_id="course-1", lecture_id="lecture-1")
    assert progress.turns[1].independent_attempt is False
    assert progress.turns[1].support_before_attempt is True


def test_assistance_and_evidence_survive_a_fresh_store_instance(tmp_path) -> None:
    layout = StorageLayout(tmp_path)
    store = CoachingProgressStore(layout)
    context = store.context(
        user_id="student-1",
        course_id="course-1",
        lecture_id="lecture-1",
        gate_id="gate-1",
        gate_title="Model selection",
    )
    policy = scaffold_policy_for_tutor_turn(
        attendance="absent",
        delayed_transfer_due=False,
        last_gate_status=None,
        needs_evidence_count=0,
        prior_assistance=False,
    )
    store.record_turn(
        user_id="student-1",
        course_id="course-1",
        lecture_id="lecture-1",
        context=context,
        policy=policy,
        decision=QualityGateDecision(
            gate_id="gate-1",
            status=QualityGateStatus.NEEDS_EVIDENCE,
            reason="The learner connected the data and model but omitted evaluation.",
            evidence_ids=["data-model-connection"],
            missing_evidence_ids=["held-out-evaluation"],
        ),
    )

    next_context = CoachingProgressStore(layout).context(
        user_id="student-1",
        course_id="course-1",
        lecture_id="lecture-1",
        gate_id="gate-1",
        gate_title="Model selection",
    )

    assert next_context.support_before_attempt is True
    assert next_context.last_assistance_level == "worked_step"
    assert next_context.evidence_ids == ["data-model-connection"]
    assert next_context.missing_evidence_ids == ["held-out-evaluation"]


def test_learner_corrected_session_goal_is_used_on_the_next_turn(tmp_path) -> None:
    store = CoachingProgressStore(StorageLayout(tmp_path))
    context = store.context(
        user_id="student-1",
        course_id="course-1",
        lecture_id="lecture-1",
        gate_id="gate-1",
        gate_title="Model selection",
    )
    store.record_turn(
        user_id="student-1",
        course_id="course-1",
        lecture_id="lecture-1",
        context=context,
        policy=_policy(context),
        decision=_decision(QualityGateStatus.NOT_ASSESSED),
        session_goal="Compare two validation strategies for my assignment.",
    )

    next_context = store.context(
        user_id="student-1",
        course_id="course-1",
        lecture_id="lecture-1",
        gate_id="gate-1",
        gate_title="Model selection",
    )

    assert next_context.session_goal == "Compare two validation strategies for my assignment."
    assert next_context.goal_is_new is False


def test_passed_gate_schedules_delayed_unassisted_transfer_check(tmp_path) -> None:
    now = datetime(2026, 7, 13, 9, 0, tzinfo=UTC)
    store = CoachingProgressStore(StorageLayout(tmp_path))
    context = store.context(
        user_id="student-1",
        course_id="course-1",
        lecture_id="lecture-1",
        gate_id="gate-1",
        gate_title="Model selection",
        now=now,
    )
    store.record_turn(
        user_id="student-1",
        course_id="course-1",
        lecture_id="lecture-1",
        context=context,
        policy=_policy(context),
        decision=_decision(QualityGateStatus.PASSED),
        now=now,
    )

    before_due = store.context(
        user_id="student-1",
        course_id="course-1",
        lecture_id="lecture-1",
        gate_id="gate-1",
        gate_title="Model selection",
        now=now + timedelta(hours=47),
    )
    due = store.context(
        user_id="student-1",
        course_id="course-1",
        lecture_id="lecture-1",
        gate_id="gate-1",
        gate_title="Model selection",
        now=now + timedelta(hours=49),
    )

    assert before_due.delayed_transfer_due is False
    assert due.delayed_transfer_due is True


def test_passing_due_transfer_marks_it_complete_instead_of_rescheduling(tmp_path) -> None:
    now = datetime(2026, 7, 13, 9, 0, tzinfo=UTC)
    store = CoachingProgressStore(StorageLayout(tmp_path))
    initial = store.context(
        user_id="student-1",
        course_id="course-1",
        lecture_id="lecture-1",
        gate_id="gate-1",
        gate_title="Model selection",
        now=now,
    )
    store.record_turn(
        user_id="student-1",
        course_id="course-1",
        lecture_id="lecture-1",
        context=initial,
        policy=_policy(initial),
        decision=_decision(QualityGateStatus.PASSED),
        now=now,
    )
    due = store.context(
        user_id="student-1",
        course_id="course-1",
        lecture_id="lecture-1",
        gate_id="gate-1",
        gate_title="Model selection",
        now=now + timedelta(days=3),
    )
    store.record_turn(
        user_id="student-1",
        course_id="course-1",
        lecture_id="lecture-1",
        context=due,
        policy=_policy(due),
        decision=_decision(QualityGateStatus.PASSED),
        now=now + timedelta(days=3),
    )

    progress = store.read(user_id="student-1", course_id="course-1", lecture_id="lecture-1")
    assert progress.delayed_transfer is not None
    assert progress.delayed_transfer.completed_at is not None
    assert progress.turns[-1].transfer_attempt is True
    assert progress.turns[-1].independent_attempt is True


def _policy(context: AgentCoachingContext):
    return scaffold_policy_for_tutor_turn(
        attendance="present",
        delayed_transfer_due=context.delayed_transfer_due,
        last_gate_status=context.last_gate_status,
        needs_evidence_count=context.needs_evidence_count,
        prior_assistance=context.prior_assistance,
    )


def _decision(status: QualityGateStatus) -> QualityGateDecision:
    return QualityGateDecision(
        gate_id="gate-1",
        status=status,
        reason="test",
    )
