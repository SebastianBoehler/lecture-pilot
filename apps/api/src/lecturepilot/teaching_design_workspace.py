"""Private, revision-bound teaching drafts around immutable learning intent."""

from pathlib import Path
import json

from lecturepilot.course_learning_intent import LearningGoal, digest
from lecturepilot.course_practice_design_models import PracticeDesignProposal, PracticeTarget
from lecturepilot.course_practice_design_validation import validate_practice_design
from lecturepilot.durable_files import atomic_write_json
from lecturepilot.practice_evidence_catalogue import (
    compact_evidence_anchors,
    expand_evidence_ids,
    hydrate_source_refs,
)
from lecturepilot.course_practice_design_review_models import PracticeDesignReviewResult


class TeachingDesignWorkspace:
    def __init__(self, *, root: Path, source, intent, initial, catalogue, paths, authorize):
        self.root, self.source, self.intent = root, source, intent
        self.catalogue, self.paths, self.authorize = catalogue, paths, authorize
        self.goals = {goal.id: goal for goal in intent.goals}
        self.fixed = {target.id: target.revision for target in intent.fixed_targets}
        self.targets = {t.id: t.model_dump(mode="json") for t in initial.targets} if initial else {}
        self.review_digest = None
        self.review = None
        path = root / "draft.json"
        if path.exists():
            saved = json.loads(path.read_text())
            if saved["intent_revision"] != intent.revision:
                raise ValueError("Teaching repair intent changed.")
            self.targets = saved["targets"]
            self.review_digest = saved.get("review_digest")
            if saved.get("review"):
                self.review = PracticeDesignReviewResult.model_validate_json(
                    json.dumps(saved["review"])
                )
        self._check_targets()

    def _check_targets(self):
        if set(self.targets) - self.goals.keys():
            raise ValueError("Teaching draft contains unknown goals.")
        for key, data in self.targets.items():
            target = PracticeTarget.model_validate_json(json.dumps(data))
            if any(
                getattr(target, name) != getattr(self.goals[key], name)
                for name in LearningGoal.model_fields
            ):
                raise ValueError("Teaching draft changed approved intent.")
            if key in self.fixed and digest(data) != self.fixed[key]:
                raise ValueError("Teaching draft changed a professor-fixed task.")

    def read(self, target_id: str) -> dict:
        """Read one approved goal, current teaching target and last review."""
        self.authorize()
        if target_id not in self.goals:
            return {"error": "Unknown goal", "goal_ids": list(self.goals)}
        return {
            "goal": self.goals[target_id].model_dump(mode="json"),
            "fixed": target_id in self.fixed,
            "teaching": compact_evidence_anchors(self.targets.get(target_id), self.catalogue),
            "review": self.feedback(),
        }

    def write(self, **target) -> dict:
        """Replace one AI-owned teaching target, never another target or approved intent."""
        self.authorize()
        key = target.get("id")
        try:
            if key not in self.goals:
                raise ValueError("Unknown approved goal ID.")
            if key in self.fixed:
                raise ValueError("Professor-fixed teaching is read-only.")
            protected = set(LearningGoal.model_fields) - {"id"}
            if protected.intersection(target):
                raise ValueError("Approved goal fields are read-only; send only teaching details.")
            expanded = expand_evidence_ids({"targets": [target]}, self.catalogue)
            data = {**expanded["targets"][0], **self.goals[key].model_dump(mode="json")}
            bound = {"targets": [data]}
            hydrate_source_refs(bound)
            checked = PracticeTarget.model_validate_json(json.dumps(data))
            if {task.stage for task in checked.supplemental_tasks} != {
                "independent_exit",
                "delayed_transfer",
            }:
                raise ValueError("Teaching requires fresh exit and delayed task variants.")
            partial = PracticeDesignProposal(
                lecture_title=self.source.title,
                objective=self.intent.objective,
                planning_context=self.intent.planning_context,
                targets=(checked,),
            )
            validate_practice_design(partial, source=self.source, allowed_source_paths=self.paths)
        except ValueError as exc:
            return {"saved": False, "error": str(exc)}
        self.targets[key] = checked.model_dump(mode="json")
        self.save()
        return {"saved": True, "target_id": key, "missing": self.missing()}

    def edit(self, target_id: str, old_text: str, new_text: str) -> dict:
        """Replace one exact, unique text span in AI-owned teaching; preserve every other field."""
        self.authorize()
        if target_id not in self.targets or target_id in self.fixed:
            return {"saved": False, "error": "Target must exist and be AI-owned."}
        if not old_text or old_text == new_text:
            return {
                "saved": False,
                "error": "Supply a nonempty text span and an actual correction.",
            }
        wire = compact_evidence_anchors(self.targets[target_id], self.catalogue)
        for field in {*LearningGoal.model_fields, "source_refs"}:
            wire.pop(field, None)
        matches = 0

        def replace(value):
            nonlocal matches
            if isinstance(value, str):
                matches += value.count(old_text)
                return value.replace(old_text, new_text)
            if isinstance(value, dict):
                return {key: replace(item) for key, item in value.items()}
            if isinstance(value, list):
                return [replace(item) for item in value]
            return value

        changed = replace(wire)
        if matches != 1:
            return {
                "saved": False,
                "error": f"Expected one AI-owned text match, found {matches}. Read the target and use a unique span.",
            }
        return self.write(id=target_id, **changed)

    def missing(self):
        return [key for key in self.goals if key not in self.targets]

    def proposal(self):
        if self.missing():
            raise ValueError(f"Missing teaching for approved goals: {self.missing()}")
        proposal = PracticeDesignProposal.model_validate_json(
            json.dumps(
                {
                    "lecture_title": self.source.title,
                    "objective": self.intent.objective,
                    "planning_context": self.intent.planning_context.model_dump(mode="json"),
                    "targets": [self.targets[key] for key in self.goals],
                }
            )
        )
        self.intent.require_matches(proposal)
        validate_practice_design(proposal, source=self.source, allowed_source_paths=self.paths)
        return proposal

    def feedback(self):
        if self.review is None:
            return None
        return compact_evidence_anchors(self.review.model_dump(mode="json"), self.catalogue)

    def defects(self):
        return (
            [
                check
                for check in self.review.checks
                if check.severity == "critical"
                or (
                    check.severity == "warning"
                    and check.dimension in {"rubric_sufficiency", "objective_task_alignment"}
                )
            ]
            if self.review
            else []
        )

    def accepted(self):
        return (
            not self.missing()
            and self.review is not None
            and not self.defects()
            and self.review_digest == digest(self.proposal().model_dump(mode="json"))
        )

    def save(self):
        self.authorize()
        atomic_write_json(
            self.root / "draft.json",
            {
                "intent_revision": self.intent.revision,
                "targets": self.targets,
                "review_digest": self.review_digest,
                "review": self.review.model_dump(mode="json") if self.review else None,
            },
        )
