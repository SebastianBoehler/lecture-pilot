import runpy
from pathlib import Path

from lecturepilot.model_commands import checkpoint_assessment_required
from lecturepilot.coaching_task_bank import task_prompt

SCRIPT = Path(__file__).resolve().parents[3] / "scripts/benchmark_gate_models.py"


def test_every_benchmark_case_uses_the_explicit_revision_bound_checkpoint():
    benchmark = runpy.run_path(str(SCRIPT))
    for scenario in benchmark["SCENARIOS"]:
        turn = benchmark["_turn_for_scenario"](scenario)
        assert checkpoint_assessment_required(turn)
        context = turn.coaching_context
        assert context.pending_check_stage is not None
        assert context.pending_check_task_id is not None
        assert context.pending_check_prompt == task_prompt(
            turn.active_gate, context.pending_check_task_id
        )
        assert turn.analytics_context.publication_version == 1
        assert len(turn.analytics_context.learning_map_revision) == 64
        assert turn.canvas_context.source_ref == turn.active_gate.source_ref


def test_benchmark_distinguishes_false_passes_rejections_and_contract_errors():
    benchmark = runpy.run_path(str(SCRIPT))
    summarize = benchmark["summarize_results"]
    result = summarize(
        [
            {"expected": "needs_evidence", "actual": "passed"},
            {"expected": "passed", "actual": "needs_evidence"},
            {"expected": "passed", "actual": "contract_error"},
            {"expected": "passed", "actual": "provider_error"},
            {"expected": "passed", "actual": "passed"},
        ]
    )
    assert result == {
        "matched": 1,
        "total": 5,
        "false_passes": 1,
        "false_rejections": 1,
        "contract_errors": 1,
        "provider_errors": 1,
    }
