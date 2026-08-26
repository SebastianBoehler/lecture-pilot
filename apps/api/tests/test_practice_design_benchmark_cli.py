from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts/benchmark_practice_design.py"


def test_benchmark_cli_exposes_model_fixture_output_and_summary_controls() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "--proposal-model" in result.stdout
    assert "--reviewer-model" in result.stdout
    assert "--fixtures" in result.stdout
    assert "--output" in result.stdout
    assert "--summary" in result.stdout
    assert "two or more distinct reviewer models" in result.stdout
