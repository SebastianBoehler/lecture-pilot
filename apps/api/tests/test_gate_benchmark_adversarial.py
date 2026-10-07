from pathlib import Path
import sys


def test_gate_benchmark_includes_german_injection_and_length_bias_checks():
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
    from gate_benchmark_cases import SCENARIOS, _turn_for_scenario

    required = {
        "german_complete_answer",
        "german_incomplete_answer",
        "injected_grading_instruction",
        "long_irrelevant_answer",
        "concise_complete_answer",
    }
    selected = [scenario for scenario in SCENARIOS if scenario.label in required]
    assert {scenario.label for scenario in selected} == required
    for scenario in selected:
        turn = _turn_for_scenario(scenario)
        assert turn.checkpoint_gate_id == turn.active_gate.id
        assert turn.message == scenario.message
