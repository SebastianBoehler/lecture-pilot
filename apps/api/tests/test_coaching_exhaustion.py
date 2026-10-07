from lecturepilot.coaching_transitions import derive_next_transition
from lecturepilot.quality_gate_models import QualityGateStatus
from practice_gate_coaching_test_helpers import practice_gate


def test_success_without_fresh_independent_task_never_returns_a_hint():
    gate = practice_gate()
    transition = derive_next_transition(
        gate,
        current_stage="exit_support",
        current_task_id="independent-exit",
        status=QualityGateStatus.PASSED,
        exposed_task_ids=["baseline", "independent-exit"],
        exposed_hint_levels=[],
    )
    assert transition.bank_exhausted
    assert transition.support_exhausted
    assert transition.check.assistance.level == "none"
    assert transition.check.assistance.content is None


def test_failure_without_remaining_approved_support_stops_assessment_retries():
    gate = practice_gate()
    transition = derive_next_transition(
        gate,
        current_stage="exit_support",
        current_task_id="independent-exit",
        status=QualityGateStatus.NEEDS_EVIDENCE,
        exposed_task_ids=["baseline", "independent-exit"],
        exposed_hint_levels=[item.level for item in gate.hint_ladder],
    )
    assert transition.support_exhausted
