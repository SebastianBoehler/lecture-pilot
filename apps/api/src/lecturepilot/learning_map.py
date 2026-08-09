from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, Field, model_validator

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.quiz_identity import (
    canonical_quiz_id,
    is_quiz_block,
    validate_unique_quiz_ids,
)


class LearningMapEvidenceCriterion(BaseModel):
    id: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=1000)
    required: bool = True


class LearningMapGate(BaseModel):
    id: str = Field(min_length=1, max_length=160)
    concept_id: str = Field(min_length=1, max_length=160)
    title: str = Field(min_length=1, max_length=200)
    prompt: str = Field(default="", max_length=1000)
    evidence_required: str = Field(default="", max_length=1000)
    evidence_criteria: list[LearningMapEvidenceCriterion] = Field(
        default_factory=list, max_length=40
    )
    transfer_prompt: str | None = Field(default=None, max_length=1000)
    review_after_days: int = Field(default=2, ge=1, le=365)
    revision: str = Field(default="", max_length=64)
    section_id: str = Field(min_length=1, max_length=160)
    source_ref: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def derive_contract_fields(self) -> LearningMapGate:
        if not self.evidence_criteria:
            description = self.evidence_required or self.prompt
            if description:
                self.evidence_criteria = [
                    LearningMapEvidenceCriterion(id=self.id, description=description)
                ]
        self.revision = _digest(self, "revision")
        return self


class LearningMapNode(BaseModel):
    id: str = Field(min_length=1, max_length=160)
    title: str = Field(min_length=1, max_length=200)
    lecture_id: str = Field(min_length=1, max_length=120)
    section_id: str = Field(min_length=1, max_length=160)
    source_ref: str | None = Field(default=None, max_length=500)
    prerequisites: list[str] = Field(default_factory=list, max_length=20)
    gate_ids: list[str] = Field(default_factory=list, max_length=20)
    quiz_ids: list[str] = Field(default_factory=list, max_length=30)


class LearningMap(BaseModel):
    course_id: str = Field(min_length=1, max_length=120)
    lecture_id: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=200)
    revision: str = Field(default="", max_length=64)
    nodes: list[LearningMapNode] = Field(default_factory=list)
    gates: list[LearningMapGate] = Field(default_factory=list)

    @model_validator(mode="after")
    def derive_revision(self) -> LearningMap:
        self.revision = _digest(self, "revision")
        return self


def build_learning_map(document: CanvasDocument) -> LearningMap:
    validate_unique_quiz_ids(document)
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
    return LearningMap(
        course_id=document.course_id,
        lecture_id=document.lecture_id,
        title=document.title,
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


def learning_map_path(canvas_dir: Path) -> Path:
    return canvas_dir / "learning-map.json"


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
    return LearningMapGate(
        id=block.id,
        concept_id=section.id,
        title=(block.caption or section.title)[:200],
        prompt=prompt,
        evidence_required=prompt,
        evidence_criteria=[LearningMapEvidenceCriterion(id=block.id, description=prompt)],
        section_id=section.id,
        source_ref=section.source_ref or document.source_ref,
    )


def _quiz_ids(blocks: list[CanvasBlock]) -> list[str]:
    return [canonical_quiz_id(block) for block in blocks if is_quiz_block(block)]


def _digest(model: BaseModel, excluded_field: str) -> str:
    payload = model.model_dump(mode="json", exclude={excluded_field})
    canonical = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
