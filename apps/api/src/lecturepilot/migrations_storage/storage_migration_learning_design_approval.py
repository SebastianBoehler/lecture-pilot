"""One-time migration of stored draft approvals to the reduced binding.

Draft approvals keep `draft_digest`, `source_revision` and `practice_design_revision`.
The removed `learning_map_revision`, `report_revision` and `learning_intent_revision`
are provably redundant: map and report live in the same review file and every change
to them clears the approval, and the intent is part of the design revision. An approval
is only kept when every removed binding still matched its review exactly; otherwise it
was already unusable for publication and is cleared. Idempotent; dry run by default.
"""

import json
from pathlib import Path

from pydantic import ValidationError

from lecturepilot.learning_design.course_learning_design_models import LearningDesignReview
from lecturepilot.core.durable_files import atomic_write_text

_KEPT = (
    "approved_by",
    "approved_at",
    "draft_digest",
    "source_revision",
    "practice_design_revision",
)
_REMOVED = (
    "learning_intent_revision",
    "learning_map_revision",
    "report_revision",
    "acknowledged_warning_ids",
)


def migrate(storage_root: Path, *, apply: bool = False) -> dict:
    report: dict = {"apply": apply, "current": 0, "reduced": [], "cleared_stale": [], "invalid": []}
    for path in sorted(storage_root.glob("courses/*/*/**/learning-design.json")):
        name = str(path.relative_to(storage_root))
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            approval = payload.get("approval")
            if not approval or not set(_REMOVED) & approval.keys():
                LearningDesignReview.model_validate(payload)
                report["current"] += 1
                continue
            outcome = "reduced" if _still_bound(payload, approval) else "cleared_stale"
            payload["approval"] = (
                {key: approval[key] for key in _KEPT} if outcome == "reduced" else None
            )
            migrated = LearningDesignReview.model_validate(payload)
        except (OSError, ValueError, ValidationError, KeyError) as exc:
            report["invalid"].append({"path": name, "reason": str(exc)[:300]})
            continue
        report[outcome].append(name)
        if apply:
            atomic_write_text(path, migrated.model_dump_json(indent=2))
    return report


def _still_bound(review: dict, approval: dict) -> bool:
    return (
        approval.get("draft_digest") == review["draft_digest"]
        and approval.get("source_revision") == review["source_revision"]
        and approval.get("practice_design_revision") == review["practice_design_revision"]
        and approval.get("learning_intent_revision") == review.get("learning_intent_revision")
        and approval.get("learning_map_revision") == review["learning_map"]["revision"]
        and approval.get("report_revision") == review["report"]["report_revision"]
    )
