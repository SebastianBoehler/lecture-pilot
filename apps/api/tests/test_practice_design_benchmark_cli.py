from datetime import UTC, datetime
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

from lecturepilot.course_practice_design_benchmark_models import (
    BENCHMARK_DIMENSIONS,
    PracticeDesignBenchmarkEvaluation,
    PracticeDesignBenchmarkReviewerJudgment,
    PracticeDesignBenchmarkReviewerSpec,
    summarize_dimension_scores,
    validate_reviewer_specs,
)
from lecturepilot.course_practice_design_benchmark_report import (
    PracticeDesignBenchmarkError,
    PracticeDesignBenchmarkFixtureResult,
    PracticeDesignBenchmarkReport,
    PracticeDesignBenchmarkReviewerResult,
)
from practice_design_review_test_helpers import passing_review
from practice_design_test_helpers import proposal


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts/benchmark_practice_design.py"


def test_benchmark_cli_documents_compact_explicit_reviewer_specs() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "--proposal-model" in result.stdout
    assert "--proposal-underlying-model" in result.stdout
    assert "--reviewer MODEL=UNDERLYING_ID[|DEPLOYMENT]" in result.stdout
    assert "--fixtures" in result.stdout
    assert "--output" in result.stdout
    assert "--summary" in result.stdout
    assert "aliases" in result.stdout
    assert "insufficient evidence of independence" in " ".join(result.stdout.split())


def test_cli_rejects_deployments_with_one_underlying_identity_before_provider_calls(
    monkeypatch, tmp_path, capsys
) -> None:
    cli = _load_cli()

    async def validating_runner(**kwargs):
        validate_reviewer_specs(kwargs["reviewers"])
        raise AssertionError("duplicate underlying identity was accepted")

    _patch_cli(monkeypatch, cli, validating_runner)
    output = tmp_path / "aliases.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(SCRIPT),
            "--proposal-underlying-model",
            "vendor/proposal-model@2026-08-01",
            "--reviewer",
            "openai/gpt-5.6=vendor/gpt-5.6@1|openai/us-east",
            "--reviewer",
            "openrouter/openai/gpt-5.6=VENDOR/GPT-5.6@1|openrouter/eu-west",
            "--output",
            str(output),
        ],
    )

    assert cli.main() == 2
    assert "Underlying reviewer model identities must be distinct" in capsys.readouterr().err
    assert not output.exists()


def test_cli_main_writes_json_prints_summary_and_returns_zero(
    monkeypatch, tmp_path, capsys
) -> None:
    cli = _load_cli()
    report = _report()
    captured: dict = {}

    async def fake_runner(**kwargs):
        captured.update(kwargs)
        return report

    _patch_cli(monkeypatch, cli, fake_runner)
    output = tmp_path / "success.json"
    monkeypatch.setattr(sys, "argv", _argv(output))

    assert cli.main() == 0
    assert PracticeDesignBenchmarkReport.model_validate_json(output.read_text()) == report
    assert captured["reviewers"] == _reviewers()
    assert captured["proposal_underlying_model_identity"] == "vendor/proposal-model@2026-08-01"
    stdout = capsys.readouterr().out
    assert "reviewers=2/2" in stdout
    assert "source_faithfulness=5.00" in stdout


@pytest.mark.parametrize("failure", ("proposal", "evaluator"))
def test_cli_main_retains_failure_report_and_returns_one(
    monkeypatch, tmp_path, capsys, failure
) -> None:
    cli = _load_cli()
    report = _report(failure=failure)

    async def fake_runner(**_kwargs):
        return report

    _patch_cli(monkeypatch, cli, fake_runner)
    output = tmp_path / f"{failure}.json"
    monkeypatch.setattr(sys, "argv", _argv(output))

    assert cli.main() == 1
    parsed = json.loads(output.read_text())
    fixture = parsed["fixtures"][0]
    if failure == "proposal":
        assert fixture["pipeline_error"]["message"] == "proposal unavailable"
    else:
        assert fixture["reviewer_results"][0]["error"]["message"] == "reviewer unavailable"
    assert "error" in capsys.readouterr().out


def test_cli_main_returns_two_without_partial_json_on_fatal_error(
    monkeypatch, tmp_path, capsys
) -> None:
    cli = _load_cli()

    async def failing_runner(**_kwargs):
        raise RuntimeError("fatal setup")

    _patch_cli(monkeypatch, cli, failing_runner)
    output = tmp_path / "fatal.json"
    monkeypatch.setattr(sys, "argv", _argv(output))

    assert cli.main() == 2
    assert not output.exists()
    assert "fatal setup" in capsys.readouterr().err


def _load_cli():
    spec = importlib.util.spec_from_file_location("benchmark_practice_design_cli_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _patch_cli(monkeypatch, cli, runner) -> None:
    monkeypatch.setattr(cli, "load_project_env", lambda: None)
    monkeypatch.setattr(cli, "load_practice_design_benchmark_fixtures", lambda _path: (object(),))
    monkeypatch.setattr(cli, "run_practice_design_benchmark", runner)


def _argv(output: Path) -> list[str]:
    return [
        str(SCRIPT),
        "--proposal-model",
        "openai/proposal-model",
        "--proposal-underlying-model",
        "vendor/proposal-model@2026-08-01",
        "--reviewer",
        "openai/reviewer-a=vendor/model-a@1|openai/us",
        "--reviewer",
        "gemini/reviewer-b=vendor/model-b@1|google/eu",
        "--output",
        str(output),
        "--summary",
    ]


def _report(failure: str | None = None) -> PracticeDesignBenchmarkReport:
    reviewers = _reviewers()
    if failure == "proposal":
        fixture = PracticeDesignBenchmarkFixtureResult(
            fixture_id="fixture-1",
            discipline="biology",
            domain="conceptual",
            provenance="synthetic",
            source_revision="a" * 64,
            proposal_model="openai/proposal-model",
            proposal_underlying_model_identity="vendor/proposal-model@2026-08-01",
            pipeline_error=PracticeDesignBenchmarkError(
                stage="proposal_pipeline",
                model="openai/proposal-model",
                message="proposal unavailable",
            ),
        )
    else:
        evaluation = _evaluation()
        results = tuple(
            PracticeDesignBenchmarkReviewerResult(
                reviewer=reviewer,
                error=(
                    PracticeDesignBenchmarkError(
                        stage="benchmark_review",
                        model=reviewer.invocation_model,
                        message="reviewer unavailable",
                    )
                    if failure == "evaluator" and index == 0
                    else None
                ),
                evaluation=(None if failure == "evaluator" and index == 0 else evaluation),
            )
            for index, reviewer in enumerate(reviewers)
        )
        judgments = tuple(
            PracticeDesignBenchmarkReviewerJudgment(
                reviewer=result.reviewer, evaluation=result.evaluation
            )
            for result in results
            if result.evaluation is not None
        )
        fixture = PracticeDesignBenchmarkFixtureResult(
            fixture_id="fixture-1",
            discipline="biology",
            domain="conceptual",
            provenance="synthetic",
            source_revision="a" * 64,
            proposal_model="openai/proposal-model",
            proposal_underlying_model_identity="vendor/proposal-model@2026-08-01",
            proposal=proposal(),
            production_review=passing_review(),
            reviewer_results=results,
            dimension_summaries=summarize_dimension_scores(judgments),
        )
    return PracticeDesignBenchmarkReport(
        generated_at=datetime(2026, 8, 26, 12, tzinfo=UTC),
        proposal_model="openai/proposal-model",
        proposal_underlying_model_identity="vendor/proposal-model@2026-08-01",
        reviewers=reviewers,
        fixtures=(fixture,),
    )


def _evaluation() -> PracticeDesignBenchmarkEvaluation:
    return PracticeDesignBenchmarkEvaluation(
        scores=[
            {
                "dimension": dimension,
                "score": 5,
                "rationale": "No material defect found.",
                "failure_examples": [],
            }
            for dimension in BENCHMARK_DIMENSIONS
        ]
    )


def _reviewers() -> tuple[PracticeDesignBenchmarkReviewerSpec, ...]:
    return (
        PracticeDesignBenchmarkReviewerSpec(
            invocation_model="openai/reviewer-a",
            underlying_model_identity="vendor/model-a@1",
            deployment_provenance="openai/us",
        ),
        PracticeDesignBenchmarkReviewerSpec(
            invocation_model="gemini/reviewer-b",
            underlying_model_identity="vendor/model-b@1",
            deployment_provenance="google/eu",
        ),
    )
