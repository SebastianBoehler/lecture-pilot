from __future__ import annotations

import hashlib
import json
from datetime import datetime
from collections.abc import Sequence
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    ValidationInfo,
    model_validator,
)

from lecturepilot.course_practice_design_context import PracticePlanningContext


_ID_PATTERN = r"^[a-z0-9][a-z0-9-]{0,79}$"
_REVISION_PATTERN = r"^[a-f0-9]{64}$"


def _normalize_nonblank_text(value: object) -> object:
    if not isinstance(value, str):
        return value
    normalized = value.strip()
    if not normalized:
        raise ValueError("Required text cannot be blank.")
    return normalized


def _freeze_collection(value: object) -> object:
    return tuple(value) if isinstance(value, list) else value


NonblankText = Annotated[str, BeforeValidator(_normalize_nonblank_text)]


class _StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, revalidate_instances="always", strict=True
    )


class PracticeEvidenceCriterion(_StrictModel):
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


class PracticeMisconception(_StrictModel):
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


class PracticeHint(_StrictModel):
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


class PracticeTarget(_StrictModel):
    id: str = Field(pattern=_ID_PATTERN)
    title: NonblankText = Field(min_length=1, max_length=200)
    outcome: NonblankText = Field(
        min_length=1,
        max_length=1_000,
        description="Source-supported conditions, observable action, and acceptable standard.",
    )
    target_invariant: NonblankText = Field(
        min_length=1,
        max_length=1_000,
        description="Knowledge or reasoning operation held constant across all task variants.",
    )
    baseline_task: NonblankText = Field(
        min_length=1,
        max_length=2_000,
        description=(
            "Diagnostic attempt before substantive help, used to choose support and never by "
            "itself treated as a mastery claim."
        ),
    )
    independent_exit_task: NonblankText = Field(
        min_length=1,
        max_length=2_000,
        description=(
            "Parallel unaided independent exit after support, hidden during instruction and "
            "requiring the same invariant without new unprovided knowledge."
        ),
    )
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
    delayed_transfer_surface_change: NonblankText = Field(
        min_length=1,
        max_length=1_000,
        description="Controlled later change in scenario, values, representation, or task form.",
    )
    evidence_criteria: Annotated[
        tuple[PracticeEvidenceCriterion, ...], BeforeValidator(_freeze_collection)
    ] = Field(min_length=1, max_length=40)
    misconceptions: Annotated[
        tuple[PracticeMisconception, ...], BeforeValidator(_freeze_collection)
    ] = Field(default_factory=tuple, max_length=40)
    hint_ladder: Annotated[tuple[PracticeHint, ...], BeforeValidator(_freeze_collection)] = Field(
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
    source_refs: Annotated[tuple[str, ...], BeforeValidator(_freeze_collection)] = Field(
        min_length=1, max_length=100
    )

    @model_validator(mode="after")
    def validate_contract(self) -> PracticeTarget:
        if self.outcome.strip().casefold() in {
            "understand",
            "know",
        } or self.outcome.strip().casefold().startswith(("understand ", "know ")):
            raise ValueError(
                "Practice target outcomes must be observable independent capabilities."
            )
        _require_distinct_tasks(self)
        _require_unique_ids(self.evidence_criteria, "evidence criterion")
        if not any(criterion.required for criterion in self.evidence_criteria):
            raise ValueError("Practice targets need at least one required evidence criterion.")
        _require_unique_ids(self.misconceptions, "misconception")
        if len(set(self.source_refs)) != len(self.source_refs):
            raise ValueError("Practice target source references must be unique.")
        _require_ordered_hints(self.hint_ladder)
        return self


class PracticeDesignProposal(_StrictModel):
    lecture_title: NonblankText = Field(min_length=1, max_length=200)
    objective: NonblankText = Field(min_length=1, max_length=1_000)
    planning_context: PracticePlanningContext
    targets: Annotated[tuple[PracticeTarget, ...], BeforeValidator(_freeze_collection)] = Field(
        min_length=1, max_length=8
    )

    @model_validator(mode="after")
    def validate_target_ids(self) -> PracticeDesignProposal:
        _require_unique_ids(self.targets, "practice target")
        return self


class PracticeDesignApproval(_StrictModel):
    approved_by: NonblankText = Field(min_length=1, max_length=160)
    approved_at: datetime
    source_revision: str = Field(pattern=_REVISION_PATTERN)
    practice_design_revision: str = Field(pattern=_REVISION_PATTERN)


class PracticeDesign(_StrictModel):
    schema_version: Literal[1] = 1
    course_id: str = Field(min_length=1, max_length=120)
    lecture_id: str = Field(min_length=1, max_length=120)
    lecture_title: NonblankText = Field(min_length=1, max_length=200)
    objective: NonblankText = Field(min_length=1, max_length=1_000)
    planning_context: PracticePlanningContext
    source_revision: str = Field(pattern=_REVISION_PATTERN)
    targets: Annotated[tuple[PracticeTarget, ...], BeforeValidator(_freeze_collection)] = Field(
        min_length=1, max_length=8
    )
    revision: str = Field(pattern=_REVISION_PATTERN)
    approval: PracticeDesignApproval | None = None

    @model_validator(mode="after")
    def validate_revision(self, info: ValidationInfo) -> PracticeDesign:
        if not (info.context or {}).get(
            "build_revision"
        ) and self.revision != practice_design_revision(self):
            raise ValueError("Practice design revision is invalid.")
        _require_unique_ids(self.targets, "practice target")
        return self

    @classmethod
    def create(cls, **values: object) -> PracticeDesign:
        candidate = cls.model_validate(
            {**values, "revision": "0" * 64}, context={"build_revision": True}
        )
        payload = candidate.model_dump(mode="json", exclude={"revision", "approval"})
        return cls.model_validate(
            {**candidate.model_dump(mode="json"), "revision": _digest(payload)}
        )


class PracticeDesignUpdate(_StrictModel):
    source_revision: str = Field(pattern=_REVISION_PATTERN)
    practice_design_revision: str = Field(pattern=_REVISION_PATTERN)
    lecture_title: NonblankText = Field(min_length=1, max_length=200)
    objective: NonblankText = Field(min_length=1, max_length=1_000)
    planning_context: PracticePlanningContext
    targets: Annotated[tuple[PracticeTarget, ...], BeforeValidator(_freeze_collection)] = Field(
        min_length=1, max_length=8
    )

    @model_validator(mode="after")
    def validate_target_ids(self) -> PracticeDesignUpdate:
        _require_unique_ids(self.targets, "practice target")
        return self


class PracticeDesignApprovalInput(_StrictModel):
    source_revision: str = Field(pattern=_REVISION_PATTERN)
    practice_design_revision: str = Field(pattern=_REVISION_PATTERN)


def practice_design_revision(design: PracticeDesign) -> str:
    payload = design.model_dump(mode="json", exclude={"revision", "approval"})
    return _digest(payload)


def _digest(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


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


def _require_unique_ids(items: Sequence[object], label: str) -> None:
    ids = [getattr(item, "id") for item in items]
    if len(set(ids)) != len(ids):
        raise ValueError(f"Practice {label} IDs must be unique.")


def _require_ordered_hints(hints: Sequence[PracticeHint]) -> None:
    levels = ["prompt", "cue", "faded_example", "worked_step"]
    indices = [levels.index(hint.level) for hint in hints]
    if indices != sorted(indices) or len(set(indices)) != len(indices):
        raise ValueError("Practice hint levels must be unique and ordered.")
