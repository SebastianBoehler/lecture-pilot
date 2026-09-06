from __future__ import annotations

from pathlib import Path

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.course_practice_design_models import PracticeDesign, PracticeTarget
from lecturepilot.course_practice_design_validation import (
    PracticeDesignValidationError,
    validate_canvas_practice_contract,
)
from lecturepilot.quiz_identity import (
    canonical_quiz_id,
    is_quiz_block,
    validate_unique_quiz_ids,
)
from lecturepilot.learning_map_models import (
    LearningMap,
    LearningMapEvidenceCriterion,
    LearningMapGate,
    LearningMapHint,
    LearningMapMisconception,
    LearningMapNode,
    require_unique_ids,
)


def build_learning_map(document: CanvasDocument, practice_design: PracticeDesign) -> LearningMap:
    validate_unique_quiz_ids(document)
    validate_learning_contract_ids(document)
    try:
        validate_canvas_practice_contract(document, practice_design)
    except PracticeDesignValidationError as exc:
        raise ValueError(str(exc)) from exc
    nodes: list[LearningMapNode] = []
    gates: list[LearningMapGate] = []
    previous_id: str | None = None
    for section in document.sections:
        section_gates = _section_gates(document, section, practice_design)
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
        objective=practice_design.objective,
        nodes=nodes,
        gates=gates,
    )


def write_learning_map(
    document: CanvasDocument, canvas_dir: Path, practice_design: PracticeDesign
) -> LearningMap:
    learning_map = build_learning_map(document, practice_design)
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
    require_unique_ids((section.id for section in document.sections), "section")
    require_unique_ids(
        (
            block.id
            for section in document.sections
            for block in section.blocks
            if block.type == "checkpoint"
        ),
        "checkpoint",
    )


def _section_gates(
    document: CanvasDocument, section: CanvasSection, practice_design: PracticeDesign
) -> list[LearningMapGate]:
    return [
        _checkpoint_gate(document, section, block, practice_design)
        for block in section.blocks
        if block.type == "checkpoint"
    ]


def _checkpoint_gate(
    document: CanvasDocument,
    section: CanvasSection,
    block: CanvasBlock,
    practice_design: PracticeDesign,
) -> LearningMapGate:
    if not block.id.startswith("practice-"):
        return _generic_checkpoint_gate(document, section, block)
    target = _target_for_checkpoint(block, practice_design)
    return LearningMapGate.create(
        id=block.id,
        concept_id=section.id,
        title=target.title,
        prompt=target.baseline_task,
        target_invariant=target.target_invariant,
        evidence_criteria=[
            LearningMapEvidenceCriterion(
                id=item.id, description=item.description, required=item.required
            )
            for item in target.evidence_criteria
        ],
        transfer_prompt=target.delayed_transfer_task,
        independent_exit_task=target.independent_exit_task,
        supplemental_tasks=list(target.supplemental_tasks),
        independent_exit_surface_change=target.independent_exit_surface_change,
        delayed_transfer_surface_change=target.delayed_transfer_surface_change,
        misconceptions=[
            LearningMapMisconception(
                id=item.id,
                description=item.description,
                diagnostic_cue=item.diagnostic_cue,
            )
            for item in target.misconceptions
        ],
        hint_ladder=[
            LearningMapHint(level=item.level, content=item.content) for item in target.hint_ladder
        ],
        review_after_days=target.review_after_days,
        section_id=section.id,
        source_ref=section.source_ref or document.source_ref,
        practice_target_id=target.id,
    )


def _target_for_checkpoint(block: CanvasBlock, design: PracticeDesign) -> PracticeTarget:
    target_id = block.id.removeprefix("practice-")
    return next(target for target in design.targets if target.id == target_id)


def _generic_checkpoint_gate(
    document: CanvasDocument, section: CanvasSection, block: CanvasBlock
) -> LearningMapGate:
    prompt = (block.text or block.caption or section.title)[:1_000]
    return LearningMapGate.create(
        id=block.id,
        concept_id=section.id,
        title=(block.caption or section.title)[:200],
        prompt=prompt,
        evidence_criteria=[LearningMapEvidenceCriterion(id=block.id, description=prompt)],
        transfer_prompt=("Apply the same reasoning to a changed case: " + prompt)[:1_000],
        review_after_days=2,
        section_id=section.id,
        source_ref=section.source_ref or document.source_ref,
    )


def _quiz_ids(blocks: list[CanvasBlock]) -> list[str]:
    return [canonical_quiz_id(block) for block in blocks if is_quiz_block(block)]
