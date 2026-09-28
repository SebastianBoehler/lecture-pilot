#!/usr/bin/env python3
"""Compare model criterion decisions with independently adjudicated human labels."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def load_rows(path: Path) -> list[dict]:
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{number}: expected an object")
        rows.append(row)
    return rows


def calibrate(predictions: list[dict], labels: list[dict]) -> dict:
    by_case: dict[str, dict[str, dict]] = defaultdict(dict)
    for row in labels:
        case = row.get("case_id")
        rater = row.get("rater_id")
        if not isinstance(case, str) or not isinstance(rater, str) or not case or not rater:
            raise ValueError("Each label needs nonempty case_id and rater_id")
        if rater in by_case[case]:
            raise ValueError(f"Duplicate rating for {case}/{rater}")
        if row.get("status") not in {"passed", "needs_evidence"}:
            raise ValueError(f"Invalid status for {case}/{rater}")
        if not isinstance(row.get("evidence_ids"), list) or not all(
            isinstance(item, str) for item in row["evidence_ids"]
        ):
            raise ValueError(f"Invalid evidence_ids for {case}/{rater}")
        by_case[case][rater] = row

    adjudicated = {}
    rater_disagreements = []
    for case, ratings in by_case.items():
        human = [row for name, row in ratings.items() if name != "adjudicated"]
        if len(human) < 2 or "adjudicated" not in ratings:
            raise ValueError(f"{case}: requires two independent ratings and an adjudicated label")
        if len({(row["status"], tuple(sorted(row["evidence_ids"]))) for row in human}) > 1:
            rater_disagreements.append(case)
        adjudicated[case] = ratings["adjudicated"]

    model_rows = defaultdict(list)
    for row in predictions:
        case = row.get("case_id", row.get("scenario"))
        if case in adjudicated:
            model_rows[str(row.get("model", "unknown"))].append((case, row))
    if not model_rows:
        raise ValueError("No prediction rows match adjudicated case IDs")

    models = {}
    for model, rows in model_rows.items():
        false_passes = []
        false_rejections = []
        criterion_errors = []
        for case, row in rows:
            truth = adjudicated[case]
            if row.get("actual") == "passed" and truth["status"] == "needs_evidence":
                false_passes.append(case)
            if row.get("actual") == "needs_evidence" and truth["status"] == "passed":
                false_rejections.append(case)
            if set(row.get("evidence_ids", [])) != set(truth["evidence_ids"]):
                criterion_errors.append(case)
        models[model] = {
            "matched_cases": len(rows),
            "false_pass_case_ids": sorted(false_passes),
            "false_rejection_case_ids": sorted(false_rejections),
            "criterion_disagreement_case_ids": sorted(criterion_errors),
        }
    return {
        "adjudicated_cases": len(adjudicated),
        "human_disagreement_case_ids": sorted(rater_disagreements),
        "models": models,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", required=True, type=Path)
    parser.add_argument("--labels", required=True, type=Path)
    args = parser.parse_args()
    predictions = json.loads(args.predictions.read_text(encoding="utf-8"))
    if not isinstance(predictions, list):
        raise ValueError("Predictions must be a JSON array")
    print(json.dumps(calibrate(predictions, load_rows(args.labels)), indent=2))


if __name__ == "__main__":
    main()
