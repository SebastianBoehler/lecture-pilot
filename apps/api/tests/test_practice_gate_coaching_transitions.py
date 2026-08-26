from datetime import datetime, timedelta

from lecturepilot.coaching_assistance import NextCheck
from lecturepilot.coaching_check_binding import bind_delayed_review
from lecturepilot.coaching_progress import CoachingProgressStore
from lecturepilot.learning_map import LearningMapGate
from lecturepilot.models import QualityGateDecision, QualityGateStatus
from lecturepilot.scaffold_policy import scaffold_policy_for_tutor_turn
from lecturepilot.storage_layout import StorageLayout
from practice_gate_coaching_test_helpers import (
    IDS,
    NOW,
    assistant_message as _assistant_message,
    check as _check,
    practice_gate as _practice_gate,
)


def test_diagnostic_pass_requires_independent_exit_before_review(tmp_path) -> None:
    store = CoachingProgressStore(StorageLayout(tmp_path))
    gate = _practice_gate()
    _bind_diagnostic(store, gate)

    diagnostic = _record(
        store,
        gate,
        status=QualityGateStatus.PASSED,
        next_check=_check(gate, gate.independent_exit_task, "none", None),
        now=NOW + timedelta(minutes=1),
    )

    progress = store.read(**IDS)
    assert diagnostic.attempt_kind == "diagnostic"
    assert diagnostic.attempt_index == 1
    assert progress.delayed_reviews == {}
    assert progress.pending_check is not None
    assert progress.pending_check.stage == "independent_exit"
    assert progress.pending_check.prompt == gate.independent_exit_task
    assert progress.pending_check.assistance_level == "none"

    independent_exit = _record(
        store,
        gate,
        status=QualityGateStatus.PASSED,
        next_check=None,
        now=NOW + timedelta(minutes=2),
    )

    progress = store.read(**IDS)
    assert independent_exit.attempt_kind == "independent_exit"
    assert independent_exit.attempt_index == 1
    assert progress.pending_check is None
    [review] = progress.delayed_reviews.values()
    assert review.scheduled_at == NOW + timedelta(minutes=2)


def test_reopening_checkpoint_does_not_reset_the_bound_independent_exit(tmp_path) -> None:
    store = CoachingProgressStore(StorageLayout(tmp_path))
    gate = _practice_gate()
    _bind_diagnostic(store, gate)
    _record(
        store,
        gate,
        status=QualityGateStatus.PASSED,
        next_check=_check(gate, gate.independent_exit_task, "none", None),
        now=NOW + timedelta(minutes=1),
    )

    store.bind_inline_checkpoint(**IDS, gate=gate, now=NOW + timedelta(minutes=2))

    pending = store.read(**IDS).pending_check
    assert pending is not None
    assert pending.stage == "independent_exit"
    assert pending.prompt == gate.independent_exit_task


def test_failed_checks_expose_approved_hints_once_and_keep_exit_indices_separate(
    tmp_path,
) -> None:
    store = CoachingProgressStore(StorageLayout(tmp_path))
    gate = _practice_gate()
    _bind_diagnostic(store, gate)

    diagnostic = _record(
        store,
        gate,
        status=QualityGateStatus.NEEDS_EVIDENCE,
        next_check=_check(gate, gate.prompt, "prompt", "Name the invariant first."),
        now=NOW + timedelta(minutes=1),
    )
    progress = store.read(**IDS)
    assert diagnostic.attempt_kind == "diagnostic"
    assert progress.pending_check is not None
    assert progress.pending_check.stage == "diagnostic_support"
    assert progress.pending_check.assistance_content == "Name the invariant first."
    assert _exposures(progress) == [(gate.revision, "prompt", "Name the invariant first.")]

    supported = _record(
        store,
        gate,
        status=QualityGateStatus.PASSED,
        next_check=_check(gate, gate.independent_exit_task, "none", None),
        now=NOW + timedelta(minutes=2),
    )
    assert supported.attempt_kind == "supported_retry"
    assert supported.attempt_index == 1
    assert store.read(**IDS).delayed_reviews == {}

    failed_exit = _record(
        store,
        gate,
        status=QualityGateStatus.NEEDS_EVIDENCE,
        next_check=_check(
            gate,
            gate.independent_exit_task,
            "cue",
            "Check the changed surface against the invariant.",
        ),
        now=NOW + timedelta(minutes=3),
    )
    progress = store.read(**IDS)
    assert failed_exit.attempt_kind == "independent_exit"
    assert failed_exit.attempt_index == 1
    assert progress.delayed_reviews == {}
    assert progress.pending_check is not None
    assert progress.pending_check.stage == "exit_support"
    assert _exposures(progress) == [
        (gate.revision, "prompt", "Name the invariant first."),
        (gate.revision, "cue", "Check the changed surface against the invariant."),
    ]

    second_support = _record(
        store,
        gate,
        status=QualityGateStatus.PASSED,
        next_check=_check(gate, gate.independent_exit_task, "none", None),
        now=NOW + timedelta(minutes=4),
    )
    second_exit = _record(
        store,
        gate,
        status=QualityGateStatus.PASSED,
        next_check=None,
        now=NOW + timedelta(minutes=5),
    )
    assert second_support.attempt_kind == "supported_retry"
    assert second_support.attempt_index == 2
    assert second_exit.attempt_kind == "independent_exit"
    assert second_exit.attempt_index == 2


def test_exhausted_hint_ladder_issues_unassisted_support_retry(tmp_path) -> None:
    store = CoachingProgressStore(StorageLayout(tmp_path))
    gate = _practice_gate(one_hint=True)
    _bind_diagnostic(store, gate)
    _record(
        store,
        gate,
        status=QualityGateStatus.NEEDS_EVIDENCE,
        next_check=_check(gate, gate.prompt, "prompt", "Name the invariant first."),
        now=NOW + timedelta(minutes=1),
    )

    event = _record(
        store,
        gate,
        status=QualityGateStatus.NEEDS_EVIDENCE,
        next_check=_check(gate, gate.prompt, "none", None),
        now=NOW + timedelta(minutes=2),
    )

    pending = store.read(**IDS).pending_check
    assert event.attempt_kind == "supported_retry"
    assert pending is not None
    assert pending.stage == "diagnostic_support"
    assert pending.assistance_level == "none"
    assert pending.assistance_content is None


def test_delayed_failure_and_support_require_another_unaided_transfer(tmp_path) -> None:
    store = CoachingProgressStore(StorageLayout(tmp_path))
    gate = _practice_gate()
    _bind_diagnostic(store, gate)
    _record(
        store,
        gate,
        status=QualityGateStatus.PASSED,
        next_check=_check(gate, gate.independent_exit_task, "none", None),
        now=NOW + timedelta(minutes=1),
    )
    _record(
        store,
        gate,
        status=QualityGateStatus.PASSED,
        next_check=None,
        now=NOW + timedelta(minutes=2),
    )
    due = NOW + timedelta(days=3)
    bind_delayed_review(store, **IDS, gate_id=gate.id, gate_revision=gate.revision, now=due)

    failed = _record(
        store,
        gate,
        status=QualityGateStatus.NEEDS_EVIDENCE,
        next_check=_check(gate, gate.transfer_prompt, "prompt", "Name the invariant first."),
        now=due + timedelta(minutes=1),
    )
    progress = store.read(**IDS)
    [review] = progress.delayed_reviews.values()
    assert failed.attempt_kind == "delayed_transfer"
    assert review.attempted_at == due + timedelta(minutes=1)
    assert review.completed_at is None
    assert progress.pending_check is not None
    assert progress.pending_check.stage == "delayed_support"

    support = _record(
        store,
        gate,
        status=QualityGateStatus.PASSED,
        next_check=_check(gate, gate.transfer_prompt, "none", None),
        now=due + timedelta(minutes=2),
    )
    progress = store.read(**IDS)
    [review] = progress.delayed_reviews.values()
    assert support.attempt_kind == "supported_retry"
    assert review.completed_at is None
    assert progress.pending_check is not None
    assert progress.pending_check.stage == "delayed_transfer"

    passed = _record(
        store,
        gate,
        status=QualityGateStatus.PASSED,
        next_check=None,
        now=due + timedelta(minutes=3),
    )
    [review] = store.read(**IDS).delayed_reviews.values()
    assert passed.attempt_kind == "delayed_transfer"
    assert passed.attempt_index == 2
    assert review.completed_at == due + timedelta(minutes=3)


def _bind_diagnostic(store: CoachingProgressStore, gate: LearningMapGate) -> None:
    store.bind_inline_checkpoint(**IDS, gate=gate, now=NOW)


def _record(
    store: CoachingProgressStore,
    gate: LearningMapGate,
    *,
    status: QualityGateStatus,
    next_check: NextCheck | None,
    now: datetime,
):
    context = store.context(
        **IDS,
        gate_id=gate.id,
        gate_revision=gate.revision,
        learning_objective="Apply the invariant independently.",
        now=now,
    )
    evidence = [item.id for item in gate.evidence_criteria] if status == "passed" else []
    return store.record_turn(
        **IDS,
        context=context,
        policy=scaffold_policy_for_tutor_turn(
            attendance="present",
            delayed_transfer_due=context.delayed_transfer_due,
            last_gate_status=context.last_gate_status,
            needs_evidence_count=context.needs_evidence_count,
            prior_assistance=context.prior_assistance,
        ),
        decision=QualityGateDecision(
            gate_id=gate.id,
            gate_revision=gate.revision,
            status=status,
            reason="Contract evidence checked.",
            evidence_ids=evidence,
            missing_evidence_ids=(
                [] if status == "passed" else [item.id for item in gate.evidence_criteria]
            ),
        ),
        next_check=next_check,
        gate=gate,
        user_message="Learner attempt.",
        assistant_message=_assistant_message(next_check),
        now=now,
    )


def _exposures(progress) -> list[tuple[str, str, str]]:
    return [
        (item.gate_revision, item.assistance_level, item.content)
        for item in sorted(progress.hint_exposures.values(), key=lambda item: item.exposed_at)
    ]
