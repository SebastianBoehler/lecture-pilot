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
from lecturepilot.course_practice_design_benchmark_models import (  # noqa: E402
    PracticeDesignBenchmarkReviewerSpec,
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
                proposal_underlying_model_identity=args.proposal_underlying_model,
                reviewers=tuple(args.reviewer),
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
        allow_abbrev=False,
        description=(
            "Run the opt-in production practice-design benchmark with separate judgments from "
            "two or more underlying model versions or materially distinct fine-tunes. "
            "Invocation slugs must be unique for consistency but are insufficient evidence of "
            "independence. Provider aliases and deployment provenance never establish it."
        ),
    )
    parser.add_argument(
        "--proposal-model",
        help="Production planner model; defaults to LECTUREPILOT_MODEL.",
    )
    parser.add_argument(
        "--proposal-underlying-model",
        required=True,
        help=(
            "Canonical underlying proposal model/version or materially distinct fine-tune "
            "identity; gateways and deployments serving the same weights use the same value."
        ),
    )
    parser.add_argument(
        "--reviewer",
        action="append",
        required=True,
        type=_reviewer_spec,
        metavar="MODEL=UNDERLYING_ID[|DEPLOYMENT]",
        help=(
            "Invocation slug, required underlying model/version or fine-tune identity, and "
            "optional deployment provenance; repeat with distinct invocation slugs and "
            "underlying identities."
        ),
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
    return parser.parse_args()


def _reviewer_spec(value: str) -> PracticeDesignBenchmarkReviewerSpec:
    invocation_model, separator, identity_and_deployment = value.partition("=")
    underlying_model_identity, deployment_separator, deployment_provenance = (
        identity_and_deployment.partition("|")
    )
    if (
        not separator
        or not invocation_model.strip()
        or not underlying_model_identity.strip()
        or (deployment_separator and not deployment_provenance.strip())
    ):
        raise argparse.ArgumentTypeError(
            "reviewer must be MODEL=UNDERLYING_ID[|DEPLOYMENT] with supplied values nonblank"
        )
    try:
        return PracticeDesignBenchmarkReviewerSpec(
            invocation_model=invocation_model.strip(),
            underlying_model_identity=underlying_model_identity.strip(),
            deployment_provenance=(
                deployment_provenance.strip() if deployment_separator else None
            ),
        )
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


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
            f"{fixture.fixture_id}: reviewers={successes}/{len(report.reviewers)}; "
            f"max_spread={disagreement}; {means or 'no scores'}"
        )
        for result in fixture.reviewer_results:
            if result.error is not None:
                deployment = (
                    f"; deployment={result.reviewer.deployment_provenance}"
                    if result.reviewer.deployment_provenance
                    else ""
                )
                print(
                    f"  {result.reviewer.invocation_model} "
                    f"[underlying={result.reviewer.underlying_model_identity}{deployment}]: "
                    f"error: {result.error.message}"
                )


if __name__ == "__main__":
    raise SystemExit(main())
