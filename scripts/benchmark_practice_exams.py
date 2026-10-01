#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api/src"))

from lecturepilot.runtime_env import load_project_env  # noqa: E402
from practice_exam_benchmark import benchmark_model  # noqa: E402
from practice_exam_benchmark_client import BenchmarkExamClient, BenchmarkMeter  # noqa: E402


async def main() -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark exam scope and solution review using a private labelled fixture."
    )
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--model", action="append", required=True)
    parser.add_argument(
        "--prices",
        type=Path,
        required=True,
        help="Verified USD per million input/cached_input/output tokens by model.",
    )
    parser.add_argument("--budget-usd", type=float, required=True)
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Also run the actual 20+ question generation and review pipeline.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Private report destination under .lecturepilot/benchmarks/.",
    )
    args = parser.parse_args()
    private_root = (ROOT / ".lecturepilot/benchmarks").resolve()
    if not args.output.resolve().is_relative_to(private_root):
        parser.error(
            "Reports contain private course evidence and must stay under .lecturepilot/benchmarks/."
        )
    if args.budget_usd <= 0:
        parser.error("Budget must be positive.")
    load_project_env()
    prices = json.loads(args.prices.read_text())
    for model in args.model:
        if model not in prices or any(
            prices[model].get(key, -1) < 0
            for key in ["input", "cached_input", "output"]
        ):
            parser.error(f"Missing verified token prices for {model}.")
    fixture = json.loads(args.fixture.read_text())
    # Scoped to this benchmark process; never changes the app's provider allowlist.
    os.environ["LECTUREPILOT_ALLOWED_MODELS"] = ",".join(args.model)
    meter = BenchmarkMeter(prices, args.budget_usd)
    report = {"fixture": str(args.fixture), "prices": prices, "models": []}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    for model in args.model:
        result = await benchmark_model(
            model, fixture, BenchmarkExamClient(meter), generate=args.generate
        )
        report["models"].append(result)
        report.update(
            estimated_usd=meter.spent_usd,
            unknown_cost_reserve_usd=meter.unknown_cost_reserve,
        )
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
        summary = {
            key: value
            for key, value in result.items()
            if key
            in [
                "model",
                "fixed_review_seconds",
                "generation_status",
                "generation_seconds",
                "fixed_review_error",
                "generation_error",
            ]
        }
        if "fixed_review" in result:
            summary["fixed_review"] = {
                key: value
                for key, value in result["fixed_review"].items()
                if key != "rows"
            }
        print(json.dumps(summary), flush=True)
    print(
        json.dumps(
            {
                "estimated_usd": meter.spent_usd,
                "unknown_cost_reserve_usd": meter.unknown_cost_reserve,
            }
        ),
        flush=True,
    )
    return int(
        any(
            "fixed_review_error" in row
            or row.get("generation_status") == "rejected_or_provider_error"
            or row.get("fixed_review", {}).get("false_accepts", 0)
            or row.get("fixed_review", {}).get("false_rejections", 0)
            for row in report["models"]
        )
    )


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
