#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api/src"))

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection  # noqa: E402
from lecturepilot.harness import LecturePilotHarness  # noqa: E402
from lecturepilot.models import AgentTurnInput, AttendanceStatus, CanvasState  # noqa: E402
from lecturepilot.providers import DEFAULT_MODEL, ProviderRegistry  # noqa: E402


@dataclass(frozen=True)
class GateScenario:
    lecture_id: str
    label: str
    attendance: AttendanceStatus
    message: str
    expected_status: str


SCENARIOS = (
    GateScenario(
        "lecture-01",
        "weak_intro_answer",
        AttendanceStatus.PRESENT,
        "Machine learning predicts labels from examples.",
        "needs_evidence",
    ),
    GateScenario(
        "lecture-01",
        "strong_intro_answer",
        AttendanceStatus.PRESENT,
        (
            "Supervised classification predicts a target label from training data. "
            "A model is optimized with a loss, then validation or test data checks generalization."
        ),
        "passed",
    ),
    GateScenario(
        "lecture-02",
        "weak_generalization_answer",
        AttendanceStatus.ABSENT,
        "Generalization means the model works later.",
        "needs_evidence",
    ),
    GateScenario(
        "lecture-02",
        "strong_generalization_answer",
        AttendanceStatus.PRESENT,
        (
            "We train on training data, use validation or held-out test data to estimate "
            "generalization, and inspect false positive or recall rates because the classifier "
            "threshold changes the decision rates."
        ),
        "passed",
    ),
    GateScenario(
        "lecture-03",
        "weak_bayes_answer",
        AttendanceStatus.PRESENT,
        "The posterior is P(C|X), so Bayes updates a belief.",
        "needs_evidence",
    ),
    GateScenario(
        "lecture-03",
        "strong_bayes_answer",
        AttendanceStatus.PRESENT,
        (
            "The posterior P(C|X) combines prior, likelihood, and evidence P(X). "
            "The classifier then chooses a decision, while loss or false-positive cost "
            "changes the risk-sensitive threshold."
        ),
        "passed",
    ),
)


async def main() -> int:
    args = _parse_args()
    _load_dotenv(ROOT / ".env")
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
    harness = LecturePilotHarness(provider_registry=ProviderRegistry.from_env(model))
    rows = []
    for scenario in SCENARIOS:
        row = {"model": model, "scenario": scenario.label, "expected": scenario.expected_status}
        try:
            result = await harness.run_turn(_turn_for_scenario(scenario))
            status = result.quality_gate.status.value if result.quality_gate else "missing"
            row.update(
                {
                    "actual": status,
                    "ok": status == scenario.expected_status,
                    "model_returned": result.model,
                    "message": result.message[:240],
                }
            )
        except Exception as exc:
            row.update({"actual": "error", "ok": False, "error": str(exc)})
        rows.append(row)
    return rows


def _turn_for_scenario(scenario: GateScenario) -> AgentTurnInput:
    return AgentTurnInput(
        user_id="provider-benchmark-user",
        course_id="martius-ml",
        lecture_id=scenario.lecture_id,
        attendance=scenario.attendance,
        message=scenario.message,
        canvas_state=CanvasState(focused_section_id=_focused_section_id(scenario.lecture_id)),
        canvas_context=_canvas_for_lecture(scenario.lecture_id),
    )


def _canvas_for_lecture(lecture_id: str) -> CanvasDocument:
    section_id, title, text = _canvas_seed(lecture_id)
    return CanvasDocument(
        id=f"benchmark-{lecture_id}",
        course_id="martius-ml",
        lecture_id=lecture_id,
        title=title,
        source_kind="generated",
        source_ref="benchmark scenario",
        workspace_path=f".lecturepilot/benchmark/{lecture_id}/canvas/index.md",
        sections=[
            CanvasSection(
                id=section_id,
                title=title,
                blocks=[CanvasBlock(id=f"{section_id}-p-1", type="paragraph", text=text)],
            )
        ],
    )


def _canvas_seed(lecture_id: str) -> tuple[str, str, str]:
    if lecture_id == "lecture-01":
        return (
            "what-is-machine-learning",
            "Machine learning setup",
            "Machine learning connects data, model, loss, optimization, and generalization.",
        )
    if lecture_id == "lecture-02":
        return (
            "generalization-foundations",
            "Generalization and classifier evaluation",
            "Held-out validation and test sets estimate generalization and classifier errors.",
        )
    return (
        "bayesian-decision-theory-the-aim",
        "Bayesian decision theory",
        "Bayes turns prior, likelihood, and evidence into a posterior for decisions under risk.",
    )


def _focused_section_id(lecture_id: str) -> str:
    return _canvas_seed(lecture_id)[0]


def _print_table(rows: list[dict]) -> None:
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
    parser = argparse.ArgumentParser(description="Benchmark provider gate behavior outside CI.")
    parser.add_argument("--model", action="append", help="Model slug, e.g. gemini/gemini-2.5-flash")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
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
