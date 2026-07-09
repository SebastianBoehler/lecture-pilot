from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.learning_gates import gate_spec_for_lecture


class LearningMapGate(BaseModel):
    id: str = Field(min_length=1, max_length=160)
    concept_id: str = Field(min_length=1, max_length=160)
    title: str = Field(min_length=1, max_length=200)
    prompt: str = Field(default="", max_length=1000)
    evidence_required: str = Field(default="", max_length=1000)
    section_id: str = Field(min_length=1, max_length=160)
    source_ref: str | None = Field(default=None, max_length=500)


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
    nodes: list[LearningMapNode] = Field(default_factory=list)
    gates: list[LearningMapGate] = Field(default_factory=list)


def build_learning_map(document: CanvasDocument) -> LearningMap:
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


def learning_map_path(canvas_dir: Path) -> Path:
    return canvas_dir / "learning-map.json"


def _section_gates(document: CanvasDocument, section: CanvasSection) -> list[LearningMapGate]:
    gates = [
        _checkpoint_gate(document, section, block)
        for block in section.blocks
        if block.type == "checkpoint"
    ]
    lecture_gate = _lecture_gate_for_section(document, section)
    return [*gates, *([lecture_gate] if lecture_gate else [])]


def _checkpoint_gate(
    document: CanvasDocument,
    section: CanvasSection,
    block: CanvasBlock,
) -> LearningMapGate:
    return LearningMapGate(
        id=block.id,
        concept_id=section.id,
        title=block.caption or section.title,
        prompt=block.text or "",
        evidence_required="Student explains the checkpoint evidence in their own words.",
        section_id=section.id,
        source_ref=section.source_ref or document.source_ref,
    )


def _lecture_gate_for_section(
    document: CanvasDocument,
    section: CanvasSection,
) -> LearningMapGate | None:
    spec = gate_spec_for_lecture(document.lecture_id)
    if spec.lecture_id != document.lecture_id:
        return None
    target_section_id = spec.pending_target.section_id
    section_ids = {candidate.id for candidate in document.sections}
    if target_section_id not in section_ids:
        target_section_id = spec.passed_target.section_id
    if section.id != target_section_id:
        return None
    evidence = "; ".join(rule.label for rule in spec.rules)
    return LearningMapGate(
        id=spec.gate_id,
        concept_id=section.id,
        title=spec.title,
        prompt=f"Demonstrate the learning outcome for {spec.title}.",
        evidence_required=evidence,
        section_id=section.id,
        source_ref=section.source_ref or document.source_ref,
    )


def _quiz_ids(blocks: list[CanvasBlock]) -> list[str]:
    return [
        block.component_id or block.id for block in blocks if block.type in {"quiz", "component"}
    ]
