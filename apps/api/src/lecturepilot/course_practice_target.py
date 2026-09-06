from __future__ import annotations

from collections.abc import Sequence
from typing import Annotated, Literal

from pydantic import BeforeValidator, Field, model_validator

from lecturepilot.course_practice_design_contract import (
    NonblankText,
    StrictPracticeDesignModel,
    freeze_collection,
    require_observable_outcome,
)
from lecturepilot.course_practice_design_evidence import PracticeSourceAnchor, anchored_source_paths

_ID_PATTERN = r"^[a-z0-9][a-z0-9-]{0,79}$"


class PracticeEvidenceCriterion(StrictPracticeDesignModel):
    id: str = Field(pattern=_ID_PATTERN)
    description: NonblankText = Field(
        min_length=1,
        max_length=1_000,
        description=(
            "One atomic, observable unit of learner evidence that can be judged from the work "
            "without passing on a keyword alone. Required criteria collectively cover the invariant."
        ),
    )
    required: bool = True
    source_anchor: PracticeSourceAnchor | None = None

    @model_validator(mode="after")
    def require_source_anchor(self) -> PracticeEvidenceCriterion:
        if self.required and self.source_anchor is None:
            raise ValueError("Required evidence criteria need an exact source anchor.")
        return self


class PracticeMisconception(StrictPracticeDesignModel):
    id: str = Field(pattern=_ID_PATTERN)
    description: NonblankText = Field(
        min_length=1,
        max_length=1_000,
        description=(
            "A plausible incorrect reasoning pattern inside this target's boundary; do not use "
            "an unrelated error, an unstated prerequisite, or merely a missing final answer."
        ),
    )
    diagnostic_cue: NonblankText = Field(
        min_length=1,
        max_length=1_000,
        description="Observable evidence in learner work that distinguishes this misconception.",
    )
    source_anchor: PracticeSourceAnchor


class PracticeHint(StrictPracticeDesignModel):
    level: Literal["prompt", "cue", "faded_example", "worked_step"] = Field(
        description=(
            "Approved support level: prompt asks the learner to inspect or plan without domain "
            "answer content; cue names the relevant principle or representation but not the next "
            "answer; faded_example gives an analogous partial example with a learner-owned step; "
            "worked_step gives one justified step and then returns a new step to the learner."
        )
    )
    content: NonblankText = Field(
        min_length=1,
        max_length=2_000,
        description="Approved hint content containing only the minimum next information.",
    )
    source_anchor: PracticeSourceAnchor


class PracticeTarget(StrictPracticeDesignModel):
    id: str = Field(pattern=_ID_PATTERN)
    title: NonblankText = Field(min_length=1, max_length=200)
    outcome: NonblankText = Field(
        min_length=1,
        max_length=1_000,
        description="Source-supported conditions, observable action, and acceptable standard.",
    )
    outcome_anchor: PracticeSourceAnchor
    target_invariant: NonblankText = Field(
        min_length=1,
        max_length=1_000,
        description="Knowledge or reasoning operation held constant across all task variants.",
    )
    target_invariant_anchor: PracticeSourceAnchor
    baseline_task: NonblankText = Field(
        min_length=1,
        max_length=2_000,
        description=(
            "Diagnostic attempt before substantive help, used to choose support and never by "
            "itself treated as a mastery claim."
        ),
    )
    baseline_task_anchor: PracticeSourceAnchor
    independent_exit_task: NonblankText = Field(
        min_length=1,
        max_length=2_000,
        description=(
            "Parallel unaided independent exit after support, hidden during instruction and "
            "requiring the same invariant without new unprovided knowledge."
        ),
    )
    independent_exit_task_anchor: PracticeSourceAnchor
    independent_exit_surface_change: NonblankText = Field(
        min_length=1,
        max_length=1_000,
        description="Controlled surface change from the diagnostic to the independent exit.",
    )
    delayed_transfer_task: NonblankText = Field(
        min_length=1,
        max_length=2_000,
        description=(
            "Delayed changed-form transfer assessment preserving the invariant without new "
            "unprovided knowledge."
        ),
    )
    delayed_transfer_task_anchor: PracticeSourceAnchor
    delayed_transfer_surface_change: NonblankText = Field(
        min_length=1,
        max_length=1_000,
        description="Controlled later change in scenario, values, representation, or task form.",
    )
    evidence_criteria: Annotated[
        tuple[PracticeEvidenceCriterion, ...], BeforeValidator(freeze_collection)
    ] = Field(min_length=1, max_length=40)
    misconceptions: Annotated[
        tuple[PracticeMisconception, ...], BeforeValidator(freeze_collection)
    ] = Field(default_factory=tuple, max_length=40)
    hint_ladder: Annotated[tuple[PracticeHint, ...], BeforeValidator(freeze_collection)] = Field(
        default_factory=tuple, max_length=4
    )
    review_after_days: int = Field(
        ge=1,
        le=365,
        description=(
            "Operational proposed review interval informed by the available context, not a claim "
            "that the model selected a scientifically optimal delay."
        ),
    )
    source_refs: Annotated[tuple[str, ...], BeforeValidator(freeze_collection)] = Field(
        min_length=1, max_length=100
    )

    @model_validator(mode="after")
    def validate_contract(self) -> PracticeTarget:
        require_observable_outcome(self.outcome)
        _require_distinct_tasks(self)
        require_unique_ids(self.evidence_criteria, "evidence criterion")
        if not any(criterion.required for criterion in self.evidence_criteria):
            raise ValueError("Practice targets need at least one required evidence criterion.")
        require_unique_ids(self.misconceptions, "misconception")
        if len(set(self.source_refs)) != len(self.source_refs):
            raise ValueError("Practice target source references must be unique.")
        if tuple(self.source_refs) != anchored_source_paths(self):
            raise ValueError(
                "Practice target source references must exactly match its field-level anchors."
            )
        _require_ordered_hints(self.hint_ladder)
        return self


def _require_distinct_tasks(target: PracticeTarget) -> None:
    normalized = {
        " ".join(value.split()).casefold()
        for value in (
            target.baseline_task,
            target.independent_exit_task,
            target.delayed_transfer_task,
        )
    }
    if "" in normalized:
        raise ValueError("Practice target task variants cannot be blank.")
    if len(normalized) != 3:
        raise ValueError("Practice target task variants must differ.")


def require_unique_ids(items: Sequence[object], label: str) -> None:
    ids = [getattr(item, "id") for item in items]
    if len(set(ids)) != len(ids):
        raise ValueError(f"Practice {label} IDs must be unique.")


def _require_ordered_hints(hints: Sequence[PracticeHint]) -> None:
    levels = ["prompt", "cue", "faded_example", "worked_step"]
    indices = [levels.index(hint.level) for hint in hints]
    if indices != sorted(indices) or len(set(indices)) != len(indices):
        raise ValueError("Practice hint levels must be unique and ordered.")
