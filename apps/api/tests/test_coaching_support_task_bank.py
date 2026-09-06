from datetime import timedelta

import pytest

from lecturepilot.coaching_progress import CoachingProgressStore
from lecturepilot.coaching_support import CoachingSupportRequest, request_support
from lecturepilot.coaching_task_bank import exposed_ids
from lecturepilot.coaching_transitions import derive_next_transition
from lecturepilot.learner_lesson_state import _goal_evidence
from lecturepilot.quality_gate_models import QualityGateStatus
from lecturepilot.storage_layout import StorageLayout
from practice_gate_coaching_test_helpers import IDS, NOW, bank_gate, practice_gate
from test_practice_gate_coaching_transitions import _record, _check


def setup_exit(tmp_path, *, bank=True):
    store = CoachingProgressStore(StorageLayout(tmp_path))
    gate = bank_gate() if bank else practice_gate()
    store.bind_inline_checkpoint(**IDS, gate=gate, now=NOW)
    _record(
        store,
        gate,
        status=QualityGateStatus.PASSED,
        next_check=_check(gate, gate.independent_exit_task, "none", None),
        now=NOW + timedelta(minutes=1),
    )
    return store, gate


def help_request(pending):
    return CoachingSupportRequest(
        gate_id=pending.gate_id,
        gate_revision=pending.gate_revision,
        task_id=pending.task_id,
        issued_at=pending.issued_at.isoformat(),
    )


def record_selected(store, gate, now):
    progress = store.read(**IDS)
    pending = progress.pending_check
    transition = derive_next_transition(
        gate,
        current_stage=pending.stage,
        current_task_id=pending.task_id,
        status=QualityGateStatus.PASSED,
        exposed_task_ids=exposed_ids(progress, gate.id, gate.revision),
        exposed_hint_levels=[item.assistance_level for item in progress.hint_exposures.values()],
    )
    return _record(
        store,
        gate,
        status=QualityGateStatus.PASSED,
        next_check=transition.check if transition else None,
        now=now,
    )


def test_help_without_answer_persists_exposure_before_return_and_fresh_check(tmp_path):
    store, gate = setup_exit(tmp_path)
    pending = store.read(**IDS).pending_check
    progress = request_support(
        store, **IDS, gate=gate, request=help_request(pending), now=NOW + timedelta(minutes=2)
    )
    assert len(progress.turns) == 1
    assert progress.pending_check.stage == "exit_support"
    assert progress.pending_check.task_id == pending.task_id
    assert progress.pending_check.assistance_content == gate.hint_ladder[0].content
    exposure = store.read(**IDS).task_exposures[f"{gate.id}@{gate.revision}@{pending.task_id}"]
    assert exposure.supported and not exposure.answered
    event = record_selected(store, gate, NOW + timedelta(minutes=3))
    progress = store.read(**IDS)
    assert event.attempt_kind == "supported_retry"
    assert progress.pending_check.task_id == "exit-fresh"
    assert progress.pending_check.task_id != pending.task_id
    assert pending.task_id in exposed_ids(progress, gate.id, gate.revision)
    assert progress.pending_check.assistance_content is None
    assert _goal_evidence(progress, [gate])[0].supported
    assert not _goal_evidence(progress, [gate])[0].independent
    record_selected(store, gate, NOW + timedelta(minutes=4))
    assert _goal_evidence(store.read(**IDS), [gate])[0].independent


@pytest.mark.parametrize(
    "field,value",
    [
        ("gate_id", "other"),
        ("gate_revision", "f" * 64),
        ("task_id", "exit-fresh"),
        ("issued_at", NOW.isoformat()),
    ],
)
def test_stale_help_does_not_mutate_state(tmp_path, field, value):
    store, gate = setup_exit(tmp_path)
    before = store.read(**IDS)
    payload = help_request(before.pending_check).model_copy(update={field: value})
    with pytest.raises(ValueError, match="changed"):
        request_support(store, **IDS, gate=gate, request=payload)
    assert store.read(**IDS) == before


def test_double_help_and_stale_assessment_are_rejected(tmp_path):
    store, gate = setup_exit(tmp_path)
    pending = store.read(**IDS).pending_check
    request = help_request(pending)
    request_support(store, **IDS, gate=gate, request=request)
    before = store.read(**IDS)
    with pytest.raises(ValueError, match="changed"):
        request_support(store, **IDS, gate=gate, request=request)
    assert store.read(**IDS) == before


def test_legacy_bank_exhaustion_stays_supported_and_never_schedules_review(tmp_path):
    store, gate = setup_exit(tmp_path, bank=False)
    request_support(
        store,
        **IDS,
        gate=gate,
        request=help_request(store.read(**IDS).pending_check),
        now=NOW + timedelta(minutes=2),
    )
    record_selected(store, gate, NOW + timedelta(minutes=3))
    progress = store.read(**IDS)
    assert progress.pending_check.stage == "exit_support"
    assert progress.pending_check.bank_exhausted
    assert not progress.delayed_reviews
    assert not _goal_evidence(progress, [gate])[0].independent


def test_delayed_help_before_answer_selects_fresh_delayed_task(tmp_path):
    from lecturepilot.coaching_check_binding import bind_delayed_review

    store, gate = setup_exit(tmp_path)
    record_selected(store, gate, NOW + timedelta(minutes=2))
    due = NOW + timedelta(days=3)
    pending = bind_delayed_review(
        store, **IDS, gate_id=gate.id, gate_revision=gate.revision, now=due
    )
    request_support(store, **IDS, gate=gate, request=help_request(pending), now=due)
    record_selected(store, gate, due + timedelta(minutes=1))
    progress = store.read(**IDS)
    assert progress.pending_check.stage == "delayed_transfer"
    assert progress.pending_check.task_id == "delayed-fresh"
    record_selected(store, gate, due + timedelta(minutes=2))
    assert _goal_evidence(store.read(**IDS), [gate])[0].delayed


def test_help_invalidates_inflight_assessment_binding(tmp_path, monkeypatch):
    store, gate = setup_exit(tmp_path)
    context = store.context(
        **IDS,
        gate_id=gate.id,
        gate_revision=gate.revision,
        learning_objective="Apply the invariant.",
    )
    request_support(store, **IDS, gate=gate, request=help_request(store.read(**IDS).pending_check))
    before = store.read(**IDS)
    monkeypatch.setattr(store, "context", lambda **kwargs: context)
    with pytest.raises(ValueError, match="not bound"):
        _record(
            store,
            gate,
            status=QualityGateStatus.PASSED,
            next_check=None,
            now=NOW + timedelta(minutes=3),
        )
    assert store.read(**IDS) == before


def test_evidence_retains_earlier_supported_success_after_turn_history_is_trimmed(tmp_path):
    store, gate = setup_exit(tmp_path)
    request_support(
        store,
        **IDS,
        gate=gate,
        request=help_request(store.read(**IDS).pending_check),
        now=NOW + timedelta(minutes=2),
    )
    record_selected(store, gate, NOW + timedelta(minutes=3))
    progress = store.read(**IDS)
    progress.turns = []
    store._write(**IDS, progress=progress)
    evidence = _goal_evidence(store.read(**IDS), [gate])[0]
    assert evidence.supported and not evidence.independent
