import runpy
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_practice_exam_review import EVIDENCE, _review
from test_practice_exam_validation import _exam


SCRIPT_ROOT = Path(__file__).resolve().parents[3] / "scripts"


def _benchmark(monkeypatch):
    monkeypatch.syspath_prepend(str(SCRIPT_ROOT))
    return runpy.run_path(str(SCRIPT_ROOT / "practice_exam_benchmark.py"))


def test_benchmark_scores_wrong_key_rejection_separately_from_valid_controls(monkeypatch):
    benchmark = _benchmark(monkeypatch)
    exam = _exam()
    review = _review()
    review["reviews"][0]["solved_answer_index"] = 0
    review["reviews"][1]["verdict"] = "fail"
    gold = {q.id: {"valid": q.id != "q-01", "category": "control"} for q in exam.questions}
    result = benchmark["score_reviews"](review, exam, EVIDENCE, {"lecture-01:risk"}, gold)
    assert result["false_accepts"] == 0
    assert result["false_rejections"] == 1
    assert result["contract_errors"] == 1
    assert result["total"] == 20


def test_benchmark_cannot_hide_missing_review_rows(monkeypatch):
    benchmark = _benchmark(monkeypatch)
    exam = _exam()
    gold = {q.id: {"valid": True, "category": "control"} for q in exam.questions}
    result = benchmark["score_reviews"]({"reviews": []}, exam, EVIDENCE, {"lecture-01:risk"}, gold)
    assert result["contract_errors"] == result["false_rejections"] == 20


def test_benchmark_budget_reserves_output_and_retry(monkeypatch):
    _benchmark(monkeypatch)
    from practice_exam_benchmark_client import BenchmarkBudgetExceeded, BenchmarkMeter

    meter = BenchmarkMeter({"openai/test": {"input": 2, "cached_input": 0.1, "output": 10}}, 0.01)
    with pytest.raises(BenchmarkBudgetExceeded):
        meter.reserve("openai/test", [], {}, 20000)


def test_benchmark_cost_counts_reasoning_once_and_discounts_cached_input(monkeypatch):
    _benchmark(monkeypatch)
    from practice_exam_benchmark_client import BenchmarkMeter

    meter = BenchmarkMeter({"openai/test": {"input": 2, "cached_input": 0.1, "output": 10}}, 1)
    response = SimpleNamespace(
        usage={
            "prompt_tokens": 1000,
            "completion_tokens": 2000,
            "prompt_tokens_details": {"cached_tokens": 500},
            "completion_tokens_details": {"reasoning_tokens": 1500},
        }
    )
    meter.record_response(response, model="openai/test")
    assert meter.spent_usd == pytest.approx(0.02105)


@pytest.mark.asyncio
async def test_benchmark_uses_requested_model_for_reviews_despite_production_critic(monkeypatch):
    _benchmark(monkeypatch)
    import practice_exam_benchmark_client as module
    from lecturepilot.models import ProviderSettings, ProviderCapability

    monkeypatch.setenv("LECTUREPILOT_CRITIC_MODEL", "openai/other-critic")
    calls = []

    async def complete(**kwargs):
        calls.append(kwargs)
        return {"reviews": []}

    monkeypatch.setattr(module, "native_completion", complete)
    settings = ProviderSettings(
        provider="openai",
        model="openai/benchmark",
        api_key_env="OPENAI_API_KEY",
        capabilities={ProviderCapability.CHAT, ProviderCapability.STRUCTURED_JSON},
    )
    meter = module.BenchmarkMeter(
        {"openai/benchmark": {"input": 2, "cached_input": 0.1, "output": 10}}, 5
    )
    await module.BenchmarkExamClient(meter).complete_exam(
        settings=settings,
        messages=[],
        max_tokens=1000,
        response_format={
            "json_schema": {
                "name": "lecturepilot_practice_exam_review",
                "schema": {"type": "object"},
            }
        },
    )
    assert calls[0]["settings"].model == "openai/benchmark"
    assert calls[0].get("tier") is None
    assert calls[0]["recorder"] is meter


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "prices", [{}, {"openai/benchmark": {"input": float("nan"), "cached_input": 0, "output": 1}}]
)
async def test_benchmark_rejects_unverified_prices_before_provider_call(monkeypatch, prices):
    _benchmark(monkeypatch)
    import practice_exam_benchmark_client as module

    calls = []

    async def complete(**kwargs):
        calls.append(kwargs)
        return {}

    monkeypatch.setattr(module, "native_completion", complete)
    with pytest.raises(module.BenchmarkBudgetExceeded, match="verified"):
        await module.BenchmarkExamClient(module.BenchmarkMeter(prices, 5)).complete_exam(
            settings=SimpleNamespace(model="openai/benchmark"),
            messages=[],
            max_tokens=1000,
            response_format={
                "json_schema": {
                    "name": "lecturepilot_practice_exam_review",
                    "schema": {"type": "object"},
                }
            },
        )
    assert calls == []


@pytest.mark.parametrize("budget", [float("nan"), float("inf"), -1, 0])
def test_benchmark_rejects_invalid_budget_before_provider_work(monkeypatch, budget):
    _benchmark(monkeypatch)
    from practice_exam_benchmark_client import BenchmarkBudgetExceeded, BenchmarkMeter

    with pytest.raises(BenchmarkBudgetExceeded, match="finite"):
        BenchmarkMeter({}, budget)
