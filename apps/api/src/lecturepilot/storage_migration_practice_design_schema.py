"""One-time migration of stored practice designs to the goals-first schema 2.

Schema-1 designs (full-plan approval) become schema-2 learning-intent designs:

- A current full approval becomes an approved learning intent by the same professor at the
  same time. Every target is fixed, so the approved goals, their order, the constraints and
  all approved tasks/rubrics stay professor-owned exactly as approved.
- An unapproved or stale design keeps its goals and tasks as unapproved intent.
- Schema-2 files only lose the retired, always-null ``approval`` key (same revision).

The design revision of converted schema-1 designs changes, so unpublished drafts bound to
them must be regenerated (they fail closed). Published canvases carry their own binding and
are unaffected. The previous file is archived privately in the design history first.
Files the current reader already rejects are reported and left untouched.
"""

import json
from pathlib import Path
from types import SimpleNamespace

from pydantic import ValidationError

from lecturepilot.course_learning_intent import LearningIntent, LearningIntentApproval, digest
from lecturepilot.course_practice_design_context import PracticePlanningContext
from lecturepilot.course_practice_design_files import locked_design_file, write_design_file
from lecturepilot.course_practice_design_models import PracticeDesign
from lecturepilot.course_practice_design_review_models import PracticeDesignQualityReview
from lecturepilot.course_practice_target import PracticeTarget

_PATTERN = "courses/*/*/builder/practice-designs/*.json"


class _Invalid(ValueError):
    pass


def migrate(storage_root: Path, *, apply: bool = False) -> dict:
    """Return a report; write only with ``apply`` (dry run by default). Idempotent."""
    report: dict = {
        "apply": apply,
        "current": 0,
        "stripped_null_approval": [],
        "converted_approved": [],
        "converted_unapproved": [],
        "invalid": [],
    }
    for path in sorted(storage_root.glob(_PATTERN)):
        name = str(path.relative_to(storage_root))
        with locked_design_file(path):
            try:
                payload = json.loads(path.read_bytes())
                outcome, design = _migrated(payload)
            except (OSError, ValueError, ValidationError) as exc:
                report["invalid"].append({"path": name, "reason": str(exc)[:300]})
                continue
            if design is None:
                report["current"] += 1
                continue
            report[outcome].append(name)
            if apply:
                write_design_file(path, design)
    return report


def _migrated(payload: dict) -> tuple[str, PracticeDesign | None]:
    if not isinstance(payload, dict):
        raise _Invalid("Stored practice design is not an object.")
    approval = payload.get("approval")
    schema = payload.get("schema_version", 1)
    if schema not in (1, 2):
        raise _Invalid("Unknown practice design schema.")
    review = payload.get("quality_review")
    review = review and PracticeDesignQualityReview.model_validate_json(json.dumps(review))
    if review and (
        review.source_revision != payload["source_revision"]
        or review.practice_design_revision != payload["revision"]
    ):
        raise _Invalid("Stored practice design review is stale.")
    if approval and (review is None or review.has_critical_issues):
        raise _Invalid("Stored approved practice design has no passing quality review.")
    approved = bool(
        approval
        and approval["source_revision"] == payload["source_revision"]
        and approval["practice_design_revision"] == payload["revision"]
    )
    if schema == 2:
        stripped = {key: value for key, value in payload.items() if key != "approval"}
        current = PracticeDesign.model_validate_json(json.dumps(stripped))
        if "approval" not in payload:
            return "current", None
        if not approved:  # Null or stale full approval: the goal approval stays as stored.
            return "stripped_null_approval", current
    targets = tuple(PracticeTarget.model_validate_json(json.dumps(t)) for t in payload["targets"])
    context = PracticePlanningContext.model_validate_json(json.dumps(payload["planning_context"]))
    if schema == 1:
        _require_legacy_revision(payload, targets, context)
    base = SimpleNamespace(
        source_revision=payload["source_revision"],
        objective=payload["objective"],
        planning_context=context,
        targets=targets,
    )
    fixed = tuple(target.id for target in targets) if approved else ()
    intent = LearningIntent.from_design(base, fixed_target_ids=fixed)
    if approved:
        intent = intent.model_copy(
            update={
                "approval": LearningIntentApproval.model_validate_json(
                    json.dumps(
                        {
                            "approved_by": approval["approved_by"],
                            "approved_at": approval["approved_at"],
                            "intent_revision": intent.revision,
                        }
                    )
                )
            }
        )
    design = PracticeDesign.create(
        course_id=payload["course_id"],
        lecture_id=payload["lecture_id"],
        lecture_title=payload["lecture_title"],
        objective=payload["objective"],
        planning_context=context,
        source_revision=payload["source_revision"],
        targets=targets,
        learning_intent=intent,
    )
    if review:
        rebound = review.model_copy(update={"practice_design_revision": design.revision})
        design = design.model_copy(update={"quality_review": rebound})
    design = PracticeDesign.model_validate_json(design.model_dump_json())
    return ("converted_approved" if approved else "converted_unapproved"), design


def _require_legacy_revision(payload, targets, context) -> None:
    if payload.get("learning_intent") is not None:
        raise _Invalid("Schema-1 designs cannot carry a learning intent.")
    expected = {
        "schema_version": 1,
        "course_id": payload["course_id"],
        "lecture_id": payload["lecture_id"],
        "lecture_title": payload["lecture_title"],
        "objective": payload["objective"],
        "planning_context": context.model_dump(mode="json"),
        "source_revision": payload["source_revision"],
        "targets": [target.model_dump(mode="json") for target in targets],
    }
    if digest(expected) != payload.get("revision"):
        raise _Invalid("Stored schema-1 practice design revision is invalid.")
