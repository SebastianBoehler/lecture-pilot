from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator


ADDED_GATE_FIELDS = {
    "target_invariant",
    "independent_exit_surface_change",
    "delayed_transfer_surface_change",
    "misconceptions",
    "hint_ladder",
}
PRACTICE_GATE_FIELDS = ADDED_GATE_FIELDS | {"independent_exit_task"}


class LearningMapEvidenceCriterion(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    id: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=1000)
    required: bool = True


class LearningMapMisconception(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    id: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=1_000)
    diagnostic_cue: str = Field(min_length=1, max_length=1_000)


class LearningMapHint(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    level: Literal["prompt", "cue", "faded_example", "worked_step"]
    content: str = Field(min_length=1, max_length=2_000)


class LearningMapGate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    id: str = Field(min_length=1, max_length=160)
    concept_id: str = Field(min_length=1, max_length=160)
    title: str = Field(min_length=1, max_length=200)
    prompt: str = Field(min_length=1, max_length=1000)
    target_invariant: str | None = Field(default=None, min_length=1, max_length=1_000)
    evidence_criteria: list[LearningMapEvidenceCriterion] = Field(min_length=1, max_length=40)
    transfer_prompt: str = Field(min_length=1, max_length=1000)
    independent_exit_task: str | None = Field(default=None, min_length=1, max_length=2_000)
    independent_exit_surface_change: str | None = Field(
        default=None, min_length=1, max_length=1_000
    )
    delayed_transfer_surface_change: str | None = Field(
        default=None, min_length=1, max_length=1_000
    )
    misconceptions: list[LearningMapMisconception] = Field(default_factory=list, max_length=40)
    hint_ladder: list[LearningMapHint] = Field(default_factory=list, max_length=4)
    review_after_days: int = Field(ge=1, le=365)
    revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    section_id: str = Field(min_length=1, max_length=160)
    source_ref: str | None = Field(default=None, max_length=500)
    practice_target_id: str | None = Field(default=None, min_length=1, max_length=80)

    @field_validator(
        "transfer_prompt",
        "target_invariant",
        "independent_exit_task",
        "independent_exit_surface_change",
        "delayed_transfer_surface_change",
    )
    @classmethod
    def require_nonblank_contract_text(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Learning-map gate contract text must not be blank.")
        return value

    @model_validator(mode="after")
    def validate_contract(self, info: ValidationInfo) -> LearningMapGate:
        require_unique_ids(
            (criterion.id for criterion in self.evidence_criteria),
            f"evidence criterion for gate '{self.id}'",
        )
        require_unique_ids(
            (item.id for item in self.misconceptions),
            f"misconception for gate '{self.id}'",
        )
        _require_ordered_hints(self.hint_ladder)
        if self.practice_target_id is not None:
            missing = PRACTICE_GATE_FIELDS - self.model_fields_set
            empty = {
                field
                for field in PRACTICE_GATE_FIELDS - {"misconceptions", "hint_ladder"}
                if getattr(self, field) is None
            }
            if missing or empty:
                fields = ", ".join(sorted(missing | empty))
                raise ValueError(
                    f"Practice learning-map gates require explicit teaching fields: {fields}."
                )
        if not (info.context or {}).get("build_revision") and not _valid_gate_revision(self):
            raise ValueError("Learning-map gate revision is invalid.")
        return self

    @classmethod
    def create(cls, **values: object) -> LearningMapGate:
        proposal = cls.model_validate(
            {**values, "revision": "0" * 64}, context={"build_revision": True}
        )
        payload = proposal.model_dump(mode="json", exclude={"revision"})
        return cls.model_validate({**payload, "revision": digest_payload(payload)})


class LearningMapNode(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    id: str = Field(min_length=1, max_length=160)
    title: str = Field(min_length=1, max_length=200)
    lecture_id: str = Field(min_length=1, max_length=120)
    section_id: str = Field(min_length=1, max_length=160)
    source_ref: str | None = Field(default=None, max_length=500)
    prerequisites: list[str] = Field(max_length=20)
    gate_ids: list[str] = Field(max_length=20)
    quiz_ids: list[str] = Field(max_length=30)


class LearningMap(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    course_id: str = Field(min_length=1, max_length=120)
    lecture_id: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=200)
    objective: str = Field(min_length=1, max_length=1_000)
    revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    nodes: list[LearningMapNode]
    gates: list[LearningMapGate]

    @model_validator(mode="after")
    def validate_contract(self, info: ValidationInfo) -> LearningMap:
        require_unique_ids((node.id for node in self.nodes), "node")
        require_unique_ids((node.section_id for node in self.nodes), "section")
        require_unique_ids((gate.id for gate in self.gates), "gate")
        gate_ids = {gate.id for gate in self.gates}
        section_ids = {node.section_id for node in self.nodes}
        if any(set(node.gate_ids) - gate_ids for node in self.nodes):
            raise ValueError("Learning-map nodes reference unknown gates.")
        if any(gate.section_id not in section_ids for gate in self.gates):
            raise ValueError("Learning-map gates reference unknown sections.")
        if not (info.context or {}).get("build_revision") and not _valid_map_revision(self):
            raise ValueError("Learning-map revision is invalid.")
        return self

    @classmethod
    def create(cls, **values: object) -> LearningMap:
        proposal = cls.model_validate(
            {**values, "revision": "0" * 64}, context={"build_revision": True}
        )
        payload = proposal.model_dump(mode="json", exclude={"revision"})
        return cls.model_validate({**payload, "revision": digest_payload(payload)})


def digest_payload(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def require_unique_ids(ids: Iterable[str], label: str) -> None:
    seen: set[str] = set()
    for identifier in ids:
        if identifier in seen:
            raise ValueError(f"Duplicate {label} ID '{identifier}'.")
        seen.add(identifier)


def _valid_gate_revision(gate: LearningMapGate) -> bool:
    payload = gate.model_dump(mode="json", exclude={"revision"})
    if gate.revision == digest_payload(payload):
        return True
    if gate.practice_target_id is not None or ADDED_GATE_FIELDS & gate.model_fields_set:
        return False
    for field in ADDED_GATE_FIELDS:
        payload.pop(field)
    return gate.revision == digest_payload(payload)


def _valid_map_revision(learning_map: LearningMap) -> bool:
    payload = learning_map.model_dump(mode="json", exclude={"revision"})
    if learning_map.revision == digest_payload(payload):
        return True
    if any(
        gate.practice_target_id is not None or ADDED_GATE_FIELDS & gate.model_fields_set
        for gate in learning_map.gates
    ):
        return False
    for gate_payload in payload["gates"]:
        for field in ADDED_GATE_FIELDS:
            gate_payload.pop(field)
    return learning_map.revision == digest_payload(payload)


def _require_ordered_hints(hints: list[LearningMapHint]) -> None:
    levels = ["prompt", "cue", "faded_example", "worked_step"]
    indices = [levels.index(hint.level) for hint in hints]
    if indices != sorted(indices) or len(set(indices)) != len(indices):
        raise ValueError("Learning-map hint levels must be unique and ordered.")
