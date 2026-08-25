from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, model_validator


_ID_PATTERN = r"^[a-z0-9][a-z0-9-]{0,79}$"
_REVISION_PATTERN = r"^[a-f0-9]{64}$"


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class PracticeEvidenceCriterion(_StrictModel):
    id: str = Field(pattern=_ID_PATTERN)
    description: str = Field(min_length=1, max_length=1_000)
    required: bool = True


class PracticeMisconception(_StrictModel):
    id: str = Field(pattern=_ID_PATTERN)
    description: str = Field(min_length=1, max_length=1_000)
    diagnostic_cue: str = Field(min_length=1, max_length=1_000)


class PracticeHint(_StrictModel):
    level: Literal["prompt", "cue", "faded_example", "worked_step"]
    content: str = Field(min_length=1, max_length=2_000)


class PracticeTarget(_StrictModel):
    id: str = Field(pattern=_ID_PATTERN)
    title: str = Field(min_length=1, max_length=200)
    outcome: str = Field(min_length=1, max_length=1_000)
    baseline_task: str = Field(min_length=1, max_length=2_000)
    independent_exit_task: str = Field(min_length=1, max_length=2_000)
    delayed_transfer_task: str = Field(min_length=1, max_length=2_000)
    evidence_criteria: list[PracticeEvidenceCriterion] = Field(min_length=1, max_length=40)
    misconceptions: list[PracticeMisconception] = Field(default_factory=list, max_length=40)
    hint_ladder: list[PracticeHint] = Field(default_factory=list, max_length=4)
    review_after_days: int = Field(ge=1, le=365)
    source_refs: list[str] = Field(min_length=1, max_length=100)

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
        _require_unique_ids(self.misconceptions, "misconception")
        if len(set(self.source_refs)) != len(self.source_refs):
            raise ValueError("Practice target source references must be unique.")
        _require_ordered_hints(self.hint_ladder)
        return self


class PracticeDesignProposal(_StrictModel):
    lecture_title: str = Field(min_length=1, max_length=200)
    objective: str = Field(min_length=1, max_length=1_000)
    targets: list[PracticeTarget] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def validate_target_ids(self) -> PracticeDesignProposal:
        _require_unique_ids(self.targets, "practice target")
        return self


class PracticeDesignApproval(_StrictModel):
    approved_by: str = Field(min_length=1, max_length=160)
    approved_at: datetime
    source_revision: str = Field(pattern=_REVISION_PATTERN)
    practice_design_revision: str = Field(pattern=_REVISION_PATTERN)


class PracticeDesign(_StrictModel):
    schema_version: Literal[1] = 1
    course_id: str = Field(min_length=1, max_length=120)
    lecture_id: str = Field(min_length=1, max_length=120)
    lecture_title: str = Field(min_length=1, max_length=200)
    objective: str = Field(min_length=1, max_length=1_000)
    source_revision: str = Field(pattern=_REVISION_PATTERN)
    targets: list[PracticeTarget] = Field(min_length=1, max_length=8)
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
    lecture_title: str = Field(min_length=1, max_length=200)
    objective: str = Field(min_length=1, max_length=1_000)
    targets: list[PracticeTarget] = Field(min_length=1, max_length=8)

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
    if len(normalized) != 3:
        raise ValueError("Practice target task variants must differ.")


def _require_unique_ids(items: list[object], label: str) -> None:
    ids = [getattr(item, "id") for item in items]
    if len(set(ids)) != len(ids):
        raise ValueError(f"Practice {label} IDs must be unique.")


def _require_ordered_hints(hints: list[PracticeHint]) -> None:
    levels = ["prompt", "cue", "faded_example", "worked_step"]
    indices = [levels.index(hint.level) for hint in hints]
    if indices != sorted(indices) or len(set(indices)) != len(indices):
        raise ValueError("Practice hint levels must be unique and ordered.")
