#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api/src"))

from lecturepilot.course_practice_design_benchmark_fixtures import (  # noqa: E402
    load_practice_design_benchmark_fixtures,
)
from lecturepilot.course_practice_design_benchmark_report import (  # noqa: E402
    PracticeDesignBenchmarkReport,
)
from lecturepilot.course_practice_design_benchmark_runner import (  # noqa: E402
    run_practice_design_benchmark,
)
from lecturepilot.providers import DEFAULT_MODEL  # noqa: E402
from lecturepilot.runtime_env import load_project_env  # noqa: E402


DEFAULT_FIXTURES = ROOT / "benchmarks/practice-design/fixtures.json"


def main() -> int:
    args = _arguments()
    load_project_env()
    proposal_model = (
        args.proposal_model or os.getenv("LECTUREPILOT_MODEL") or DEFAULT_MODEL
    )
    try:
        fixtures = load_practice_design_benchmark_fixtures(args.fixtures)
        report = asyncio.run(
            run_practice_design_benchmark(
                fixtures=fixtures,
                proposal_model=proposal_model,
                reviewer_models=tuple(args.reviewer_model),
            )
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            report.model_dump_json(indent=2) + "\n", encoding="utf-8"
        )
    except Exception as exc:
        print(f"Practice-design benchmark could not run: {exc}", file=sys.stderr)
        return 2
    print(f"Wrote benchmark report to {args.output}")
    if args.summary:
        _print_summary(report)
    return 1 if report.has_errors else 0


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the opt-in production practice-design benchmark with separate judgments from "
            "two or more distinct reviewer models."
        )
    )
    parser.add_argument(
        "--proposal-model",
        help="Production planner model; defaults to LECTUREPILOT_MODEL.",
    )
    parser.add_argument(
        "--reviewer-model",
        action="append",
        required=True,
        help="Distinct benchmark reviewer model slug; provide this flag at least twice.",
    )
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=DEFAULT_FIXTURES,
        help="Frozen synthetic/public fixture corpus JSON.",
    )
    parser.add_argument("--output", type=Path, required=True, help="JSON report path.")
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Also print concise per-fixture dimension means and disagreement.",
    )
    args = parser.parse_args()
    if len(args.reviewer_model) < 2 or len(set(args.reviewer_model)) != len(
        args.reviewer_model
    ):
        parser.error("--reviewer-model requires at least two distinct model slugs")
    return args


def _print_summary(report: PracticeDesignBenchmarkReport) -> None:
    for fixture in report.fixtures:
        if fixture.pipeline_error is not None:
            print(
                f"{fixture.fixture_id}: proposal error: {fixture.pipeline_error.message}"
            )
            continue
        successes = sum(
            result.evaluation is not None for result in fixture.reviewer_results
        )
        means = ", ".join(
            f"{item.dimension}={item.mean_score:.2f}"
            for item in fixture.dimension_summaries
        )
        spreads = [
            item.score_spread
            for item in fixture.dimension_summaries
            if item.score_spread is not None
        ]
        disagreement = str(max(spreads)) if spreads else "n/a"
        print(
            f"{fixture.fixture_id}: reviewers={successes}/{len(report.reviewer_models)}; "
            f"max_spread={disagreement}; {means or 'no scores'}"
        )
        for result in fixture.reviewer_results:
            if result.error is not None:
                print(f"  {result.reviewer_model}: error: {result.error.message}")


if __name__ == "__main__":
    raise SystemExit(main())
