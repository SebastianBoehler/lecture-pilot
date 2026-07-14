from __future__ import annotations

import os
from pathlib import Path
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[3]
PROVIDER_CHECK = REPO_ROOT / "scripts" / "check-provider-env.sh"
DEV_DEMO = REPO_ROOT / "scripts" / "dev-demo.sh"


def test_provider_check_rejects_missing_selected_provider_key() -> None:
    result = _run_check(LECTUREPILOT_MODEL="openrouter/openai/gpt-oss-120b")

    assert result.returncode == 1
    assert result.stderr == (
        "OPENROUTER_API_KEY is required for LECTUREPILOT_MODEL=openrouter/openai/gpt-oss-120b.\n"
    )


def test_provider_check_accepts_explicit_selected_provider_key() -> None:
    result = _run_check(
        LECTUREPILOT_MODEL="openrouter/openai/gpt-oss-120b",
        OPENROUTER_API_KEY="configured-for-this-repository",
    )

    assert result.returncode == 0
    assert result.stderr == ""


def test_dev_demo_has_no_sibling_key_or_model_override() -> None:
    script = DEV_DEMO.read_text()

    assert "../sunderlabs" not in script
    assert "export LECTUREPILOT_MODEL" not in script


def _run_check(**env: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(PROVIDER_CHECK)],
        env={"PATH": os.environ["PATH"], **env},
        capture_output=True,
        check=False,
        text=True,
    )
