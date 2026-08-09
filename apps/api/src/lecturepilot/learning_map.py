from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.quiz_identity import (
    canonical_quiz_id,
    is_quiz_block,
    validate_unique_quiz_ids,
)


class LearningMapEvidenceCriterion(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    id: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=1000)
    required: bool = True


class LearningMapGate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    id: str = Field(min_length=1, max_length=160)
    concept_id: str = Field(min_length=1, max_length=160)
    title: str = Field(min_length=1, max_length=200)
    prompt: str = Field(min_length=1, max_length=1000)
    evidence_criteria: list[LearningMapEvidenceCriterion] = Field(min_length=1, max_length=40)
    transfer_prompt: str = Field(min_length=1, max_length=1000)
    review_after_days: int = Field(ge=1, le=365)
    revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    section_id: str = Field(min_length=1, max_length=160)
    source_ref: str | None = Field(default=None, max_length=500)

    @field_validator("transfer_prompt")
    @classmethod
    def require_nonblank_transfer_prompt(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("transfer_prompt must not be blank")
        return value

    @model_validator(mode="after")
    def validate_contract(self, info: ValidationInfo) -> LearningMapGate:
        _require_unique_ids(
            (criterion.id for criterion in self.evidence_criteria),
            f"evidence criterion for gate '{self.id}'",
        )
        if not (info.context or {}).get("build_revision") and self.revision != _digest(
            self, "revision"
        ):
            raise ValueError("Learning-map gate revision is invalid.")
        return self

    @classmethod
    def create(cls, **values: object) -> LearningMapGate:
        proposal = cls.model_validate(
            {**values, "revision": "0" * 64}, context={"build_revision": True}
        )
        payload = proposal.model_dump(mode="json", exclude={"revision"})
        return cls.model_validate({**payload, "revision": _digest_payload(payload)})


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
        _require_unique_ids((node.id for node in self.nodes), "node")
        _require_unique_ids((node.section_id for node in self.nodes), "section")
        _require_unique_ids((gate.id for gate in self.gates), "gate")
        gate_ids = {gate.id for gate in self.gates}
        section_ids = {node.section_id for node in self.nodes}
        if any(set(node.gate_ids) - gate_ids for node in self.nodes):
            raise ValueError("Learning-map nodes reference unknown gates.")
        if any(gate.section_id not in section_ids for gate in self.gates):
            raise ValueError("Learning-map gates reference unknown sections.")
        if not (info.context or {}).get("build_revision") and self.revision != _digest(
            self, "revision"
        ):
            raise ValueError("Learning-map revision is invalid.")
        return self

    @classmethod
    def create(cls, **values: object) -> LearningMap:
        proposal = cls.model_validate(
            {**values, "revision": "0" * 64}, context={"build_revision": True}
        )
        payload = proposal.model_dump(mode="json", exclude={"revision"})
        return cls.model_validate({**payload, "revision": _digest_payload(payload)})


def build_learning_map(document: CanvasDocument) -> LearningMap:
    validate_unique_quiz_ids(document)
    validate_learning_contract_ids(document)
    nodes: list[LearningMapNode] = []
    gates: list[LearningMapGate] = []
    previous_id: str | None = None
    for section in document.sections:
        section_gates = _section_gates(document, section)
        gates.extend(section_gates)
        nodes.append(
            LearningMapNode(
                id=section.id,
                title=section.title,
                lecture_id=document.lecture_id,
                section_id=section.id,
                source_ref=section.source_ref,
                prerequisites=[previous_id] if previous_id else [],
                gate_ids=[gate.id for gate in section_gates],
                quiz_ids=_quiz_ids(section.blocks),
            )
        )
        previous_id = section.id
    return LearningMap.create(
        course_id=document.course_id,
        lecture_id=document.lecture_id,
        title=document.title,
        objective=f"Explain and apply {document.title} independently.",
        nodes=nodes,
        gates=gates,
    )


def write_learning_map(document: CanvasDocument, canvas_dir: Path) -> LearningMap:
    learning_map = build_learning_map(document)
    path = learning_map_path(canvas_dir)
    path.write_text(learning_map.model_dump_json(indent=2), encoding="utf-8")
    return learning_map


def read_learning_map(canvas_dir: Path) -> LearningMap | None:
    path = learning_map_path(canvas_dir)
    if not path.exists():
        return None
    return LearningMap.model_validate_json(path.read_text(encoding="utf-8"))


def read_strict_published_learning_map(canvas_dir: Path) -> LearningMap | None:
    path = learning_map_path(canvas_dir)
    if not path.exists():
        return None
    return LearningMap.model_validate_json(path.read_text(encoding="utf-8"), strict=True)


def learning_map_path(canvas_dir: Path) -> Path:
    return canvas_dir / "learning-map.json"


def validate_learning_contract_ids(document: CanvasDocument) -> None:
    _require_unique_ids((section.id for section in document.sections), "section")
    _require_unique_ids(
        (
            block.id
            for section in document.sections
            for block in section.blocks
            if block.type == "checkpoint"
        ),
        "checkpoint",
    )


def _section_gates(document: CanvasDocument, section: CanvasSection) -> list[LearningMapGate]:
    return [
        _checkpoint_gate(document, section, block)
        for block in section.blocks
        if block.type == "checkpoint"
    ]


def _checkpoint_gate(
    document: CanvasDocument,
    section: CanvasSection,
    block: CanvasBlock,
) -> LearningMapGate:
    prompt = (block.text or block.caption or section.title)[:1000]
    return LearningMapGate.create(
        id=block.id,
        concept_id=section.id,
        title=(block.caption or section.title)[:200],
        prompt=prompt,
        evidence_criteria=[LearningMapEvidenceCriterion(id=block.id, description=prompt)],
        transfer_prompt=(
            "Apply the same reasoning to a changed case not used in the lecture: " + prompt
        )[:1000],
        review_after_days=2,
        section_id=section.id,
        source_ref=section.source_ref or document.source_ref,
    )


def _quiz_ids(blocks: list[CanvasBlock]) -> list[str]:
    return [canonical_quiz_id(block) for block in blocks if is_quiz_block(block)]


def _digest(model: BaseModel, excluded_field: str) -> str:
    payload = model.model_dump(mode="json", exclude={excluded_field})
    canonical = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _digest_payload(payload: dict[str, object]) -> str:
    serializable = {
        key: value.model_dump(mode="json") if isinstance(value, BaseModel) else value
        for key, value in payload.items()
    }
    for key, value in serializable.items():
        if isinstance(value, list):
            serializable[key] = [
                item.model_dump(mode="json") if isinstance(item, BaseModel) else item
                for item in value
            ]
    canonical = json.dumps(serializable, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _require_unique_ids(ids: Iterable[str], label: str) -> None:
    seen: set[str] = set()
    for identifier in ids:
        if identifier in seen:
            raise ValueError(f"Duplicate {label} ID '{identifier}'.")
        seen.add(identifier)
