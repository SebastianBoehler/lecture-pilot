#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api/src"))

sys.path.insert(0, str(ROOT / "scripts"))

from gate_benchmark_cases import SCENARIOS, _turn_for_scenario  # noqa: E402
from lecturepilot.harness import LecturePilotHarness  # noqa: E402
from lecturepilot.model_client import ModelExecutionError  # noqa: E402
from lecturepilot.providers import (  # noqa: E402
    DEFAULT_MODEL,
    ProviderRegistry,
    ProviderConfigurationError,
)
from pydantic import ValidationError  # noqa: E402


async def main() -> int:
    args = _parse_args()
    _load_dotenv(ROOT / ".env.local")
    models = args.model or [os.getenv("LECTUREPILOT_MODEL") or DEFAULT_MODEL]
    rows = []
    for model in models:
        rows.extend(await _benchmark_model(model))
    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        _print_table(rows)
    return 0


async def _benchmark_model(model: str) -> list[dict]:
    registry = ProviderRegistry.from_env(model)
    registry.require_ready([])
    harness = LecturePilotHarness(provider_registry=registry)
    rows = []
    for scenario in SCENARIOS:
        row = {
            "model": model,
            "scenario": scenario.label,
            "expected": scenario.expected_status,
        }
        try:
            result = await harness.run_turn(_turn_for_scenario(scenario))
            status = (
                result.quality_gate.status.value
                if result.quality_gate
                else "contract_error"
            )
            row.update(
                {
                    "actual": status,
                    "ok": status == scenario.expected_status,
                    "model_returned": result.model,
                    "message": result.message[:240],
                }
            )
        except ModelExecutionError as exc:
            row.update({"actual": "provider_error", "ok": False, "error": str(exc)})
        except (ProviderConfigurationError, ValidationError, ValueError) as exc:
            row.update({"actual": "contract_error", "ok": False, "error": str(exc)})
        rows.append(row)
    return rows


def summarize_results(rows: list[dict]) -> dict[str, int]:
    return {
        "matched": sum(row["actual"] == row["expected"] for row in rows),
        "total": len(rows),
        "false_passes": sum(
            row["actual"] == "passed" and row["expected"] == "needs_evidence"
            for row in rows
        ),
        "false_rejections": sum(
            row["actual"] == "needs_evidence" and row["expected"] == "passed"
            for row in rows
        ),
        "contract_errors": sum(row["actual"] == "contract_error" for row in rows),
        "provider_errors": sum(row["actual"] == "provider_error" for row in rows),
    }


def _print_table(rows: list[dict]) -> None:
    print(json.dumps(summarize_results(rows)))
    passed = sum(1 for row in rows if row.get("ok"))
    print(f"Gate benchmark: {passed}/{len(rows)} scenarios matched expected status")
    for row in rows:
        marker = "OK" if row.get("ok") else "FAIL"
        print(
            f"{marker:4} {row['model']:<36} {row['scenario']:<30} "
            f"expected={row['expected']} actual={row.get('actual')}"
        )
        if row.get("error"):
            print(f"     error={row['error']}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark provider gate behavior outside CI."
    )
    parser.add_argument(
        "--model", action="append", help="Model slug, e.g. gemini/gemini-3.5-flash"
    )
    parser.add_argument(
        "--json", action="store_true", help="Print machine-readable JSON."
    )
    return parser.parse_args()


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = _strip_quotes(value.strip())


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
