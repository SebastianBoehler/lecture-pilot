import pytest
from pydantic import ValidationError

from lecturepilot.coaching_transitions import derive_next_transition
from lecturepilot.quality_gate_models import QualityGateStatus
from practice_gate_coaching_test_helpers import practice_gate


def test_supported_exit_never_reuses_exposed_canonical_task():
    gate = practice_gate()
    transition = derive_next_transition(
        gate,
        current_stage="exit_support",
        status=QualityGateStatus.PASSED,
        exposed_hint_levels=["prompt"],
        exposed_task_ids=["independent-exit"],
        current_task_id="independent-exit",
    )
    assert transition.stage == "exit_support"
    assert transition.bank_exhausted


def test_numeric_assertions_are_bounded_and_check_only_explicit_arithmetic():
    from lecturepilot.practice_task_bank import NumericConsistencyAssertion

    NumericConsistencyAssertion(operation="divide", operands=[6.0, 3.0], expected=2.0)
    with pytest.raises(ValidationError, match="consistency"):
        NumericConsistencyAssertion(operation="add", operands=[6.0, 3.0], expected=2.0)
    with pytest.raises(ValidationError):
        NumericConsistencyAssertion(operation="eval", operands=[1.0, 2.0], expected=0.0)
