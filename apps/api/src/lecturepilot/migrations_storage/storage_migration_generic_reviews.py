"""Retire generic delayed reviews without rewriting publications or attempt history."""

import json
from pathlib import Path

from lecturepilot.core.durable_files import atomic_write_json, exclusive_file_lock
from lecturepilot.learning_design.learning_map_models import LearningMap
from lecturepilot.learner.coaching_state_models import CoachingProgress


def migrate(storage_root: Path, *, apply: bool = False) -> dict:
    retired: dict[tuple[str, str], set[tuple[str, str]]] = {}
    report: dict = {"apply": apply, "updated": [], "invalid": []}
    for path in sorted(storage_root.glob("courses/*/*/canvas/lectures/*/learning-map.json")):
        try:
            learning_map = LearningMap.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            report["invalid"].append(str(path.relative_to(storage_root)))
            continue
        key = (learning_map.course_id, learning_map.lecture_id)
        retired.setdefault(key, set()).update(
            (gate.id, gate.revision) for gate in learning_map.gates if not gate.has_delayed_review
        )
    for pattern in (
        "users/*/courses/*/lectures/*/tutor-state.json",
        "previews/professors/*/courses/*/lectures/*/tutor-state.json",
    ):
        for path in sorted(storage_root.glob(pattern)):
            with exclusive_file_lock(path):
                try:
                    raw = path.read_text(encoding="utf-8")
                    CoachingProgress.model_validate_json(raw)
                    payload = json.loads(raw)
                except (OSError, ValueError):
                    report["invalid"].append(str(path.relative_to(storage_root)))
                    continue
                keys = retired.get((payload["course_id"], payload["lecture_id"]), set())
                if keys and _retire(payload, keys):
                    report["updated"].append(str(path.relative_to(storage_root)))
                    if apply:
                        atomic_write_json(path, payload)
    return report


def _retire(payload: dict, keys: set[tuple[str, str]]) -> bool:
    before = json.dumps(payload, sort_keys=True)

    def retired(record):
        return (record["gate_id"], record["gate_revision"]) in keys

    if "delayed_reviews" in payload:
        payload["delayed_reviews"] = {
            key: review for key, review in payload["delayed_reviews"].items() if not retired(review)
        }
    pending = payload.get("pending_check")
    if pending and retired(pending) and pending["stage"] in {"delayed_transfer", "delayed_support"}:
        payload["pending_check"] = None
    if "task_exposures" in payload:
        payload["task_exposures"] = {
            key: exposure
            for key, exposure in payload["task_exposures"].items()
            if not (retired(exposure) and exposure["task_id"] == "delayed-transfer")
        }
    for evidence in payload.get("goal_evidence", {}).values():
        if retired(evidence):
            evidence["delayed"] = False
    return json.dumps(payload, sort_keys=True) != before
