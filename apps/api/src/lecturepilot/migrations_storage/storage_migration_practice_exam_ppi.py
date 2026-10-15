"""Remove retired PPI fields from stored practice exams once.

Practice exams once recorded the imported PPI protocol ids they drew patterns from
(``ppi_source_ids`` on the exam, ``ppi_pattern_ids`` per question). The PPI import is gone and
the strict exam model no longer accepts those keys, so this migration drops them from every
stored ``exam.json``; questions, answers and source citations are unchanged. It is a dry run
unless ``apply=True`` and is idempotent.
"""

from __future__ import annotations

import json
from pathlib import Path

from lecturepilot.core.durable_files import atomic_write_json


def migrate(storage_root: Path, *, apply: bool = False) -> dict:
    report: dict = {
        "migration": "practice_exam_ppi",
        "applied": apply,
        "exams_scanned": 0,
        "changed_files": [],
        "errors": [],
    }
    for path in sorted(storage_root.glob("users/*/courses/*/practice-exams/*/exam.json")):
        report["exams_scanned"] += 1
        relative = str(path.relative_to(storage_root))
        try:
            exam = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            report["errors"].append({"path": relative, "error": type(exc).__name__})
            continue
        if not _strip_ppi_fields(exam):
            continue
        report["changed_files"].append(relative)
        if apply:
            atomic_write_json(path, exam)
    return report


def _strip_ppi_fields(exam: dict) -> bool:
    changed = exam.pop("ppi_source_ids", None) is not None
    for question in exam.get("questions", []):
        if isinstance(question, dict):
            changed = question.pop("ppi_pattern_ids", None) is not None or changed
    return changed
