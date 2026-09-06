"""Professor-owned learning intent, independent of generated teaching revisions."""

from datetime import datetime
from hashlib import sha256
import json
from typing import Annotated

from pydantic import BeforeValidator, Field, model_validator

from lecturepilot.course_practice_design_context import PracticePlanningContext
from lecturepilot.course_practice_design_contract import (
    NonblankText,
    StrictPracticeDesignModel,
    freeze_collection,
    require_observable_outcome,
)
from lecturepilot.course_practice_design_evidence import PracticeSourceAnchor


class LearningGoal(StrictPracticeDesignModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,79}$")
    title: NonblankText = Field(max_length=200)
    outcome: NonblankText = Field(max_length=1_000)
    outcome_anchor: PracticeSourceAnchor
    target_invariant: NonblankText = Field(max_length=1_000)
    target_invariant_anchor: PracticeSourceAnchor

    @model_validator(mode="after")
    def validate_outcome(self):
        require_observable_outcome(self.outcome)
        return self


class FixedTeachingTarget(StrictPracticeDesignModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,79}$")
    revision: str = Field(pattern=r"^[a-f0-9]{64}$")


class LearningIntentApproval(StrictPracticeDesignModel):
    approved_by: NonblankText = Field(max_length=160)
    approved_at: datetime
    intent_revision: str = Field(pattern=r"^[a-f0-9]{64}$")


class LearningIntent(StrictPracticeDesignModel):
    source_revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    objective: NonblankText = Field(max_length=1_000)
    planning_context: PracticePlanningContext
    goals: Annotated[tuple[LearningGoal, ...], BeforeValidator(freeze_collection)] = Field(
        min_length=1,
        max_length=8,
    )
    fixed_targets: Annotated[
        tuple[FixedTeachingTarget, ...], BeforeValidator(freeze_collection)
    ] = Field(default_factory=tuple, max_length=8)
    revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    approval: LearningIntentApproval | None = None

    @model_validator(mode="after")
    def validate_binding(self):
        if self.revision != digest(self.model_dump(mode="json", exclude={"revision", "approval"})):
            raise ValueError("Learning intent revision is invalid.")
        ids = [goal.id for goal in self.goals]
        fixed = [target.id for target in self.fixed_targets]
        if len(set(ids)) != len(ids) or len(set(fixed)) != len(fixed) or not set(fixed) <= set(ids):
            raise ValueError("Learning intent target identities are invalid.")
        if self.approval and self.approval.intent_revision != self.revision:
            raise ValueError("Learning intent approval is stale.")
        return self

    @classmethod
    def from_design(cls, design, *, fixed_target_ids=()):
        if not set(fixed_target_ids) <= {target.id for target in design.targets}:
            raise ValueError("Unknown fixed teaching target.")
        payload = {
            "source_revision": design.source_revision,
            "objective": design.objective,
            "planning_context": design.planning_context.model_dump(mode="json"),
            "goals": [
                goal.model_dump(mode="json")
                for goal in (
                    tuple(goal_for(target) for target in design.targets)
                    if design.targets
                    else design.learning_intent.goals
                )
            ],
            "fixed_targets": [
                {"id": target.id, "revision": digest(target.model_dump(mode="json"))}
                for target in design.targets
                if target.id in fixed_target_ids
            ],
        }
        return cls.model_validate_json(json.dumps({**payload, "revision": digest(payload)}))

    def require_matches(self, design):
        if (
            design.objective != self.objective
            or design.planning_context != self.planning_context
            or tuple(goal_for(target) for target in design.targets) != self.goals
        ):
            raise ValueError("Implementation changed protected learning goals or constraints.")
        targets = {target.id: target for target in design.targets}
        if any(
            digest(targets[fixed.id].model_dump(mode="json")) != fixed.revision
            for fixed in self.fixed_targets
        ):
            raise ValueError("Implementation changed a protected professor-fixed task.")


def goal_for(target) -> LearningGoal:
    return LearningGoal(**{key: getattr(target, key) for key in LearningGoal.model_fields})


def digest(payload) -> str:
    return sha256(
        json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def has_approved_intent(design) -> bool:
    intent = design.learning_intent
    return bool(
        intent
        and intent.approval
        and intent.source_revision == design.source_revision
        and intent.approval.intent_revision == intent.revision
    )
