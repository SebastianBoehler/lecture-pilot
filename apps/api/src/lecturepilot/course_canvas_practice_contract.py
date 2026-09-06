from __future__ import annotations

import json
from collections.abc import Sequence

from lecturepilot.canvas_models import CanvasDocument, CanvasSection
from lecturepilot.course_canvas_evidence_batches import group_evidence_sections
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_practice_design_models import PracticeDesign, PracticeTarget
from lecturepilot.course_practice_design_validation import (
    PracticeDesignValidationError,
    source_anchor_matches_section,
    validate_canvas_practice_contract,
)
from lecturepilot.course_canvas_validation import source_topic_sections


def practice_prompt_instruction(
    design: PracticeDesign,
    *,
    targets: Sequence[PracticeTarget] | None = None,
    server_owned_checkpoints: bool = False,
) -> str:
    scoped = tuple(targets) if targets is not None else design.targets
    expected = [f"practice-{target.id}" for target in scoped]
    contracts = [
        {
            "checkpoint_id": f"practice-{target.id}",
            "outcome": target.outcome,
            "target_invariant": target.target_invariant,
            "baseline_task": target.baseline_task,
            "evidence_criteria": [
                {"id": criterion.id, "description": criterion.description}
                for criterion in target.evidence_criteria
            ],
            "source_refs": target.source_refs,
        }
        for target in scoped
    ]
    checkpoint_instruction = (
        f"Approved practice-design revision: {design.revision}. "
        "The server inserts the exact approved diagnostic checkpoints before your teaching "
        "blocks in this assigned outcome-anchor section. Do not output or reproduce these "
        "baseline tasks or canonical practice-* ids. Generate instruction around their "
        "capabilities, not replacements for the approved diagnostics. "
        if server_owned_checkpoints
        else f"Approved practice-design revision: {design.revision}. The lecture must contain exactly "
        f"one checkpoint for each canonical id {json.dumps(expected)} and no other practice-* "
        "checkpoint. Each canonical checkpoint text must exactly equal its approved baseline_task; "
        "do not paraphrase, split, merge, duplicate, or move it into another block type. "
        "Place this diagnostic before substantive help on its capability, within its assigned "
        "outcome-anchor section. "
    )
    return (
        checkpoint_instruction + "Keep analogous worked examples before later formative checks. "
        "The design context calibrates vocabulary and scaffolding, not the required evidence "
        "standard. Null context fields are unknown, not permission to invent learner expertise. "
        "Use the outcome, invariant and criteria to design instruction; do not print assessed "
        "answers or hidden exit/transfer tasks next to the diagnostic. If an approved task is "
        "unsuitable, report the conflict rather than silently rewriting it. "
        f"Approved lecture objective: {json.dumps(design.objective)}. "
        f"Approved planning context: {design.planning_context.model_dump_json()}. "
        f"Applicable approved target contracts: {json.dumps(contracts)}"
    )


def section_target_assignments(
    design: PracticeDesign, sections: Sequence[CanvasSection]
) -> dict[str, tuple[PracticeTarget, ...]]:
    assignments: dict[str, list[PracticeTarget]] = {section.id: [] for section in sections}
    for target in design.targets:
        routed_paths = set(target.source_refs)
        section = next(
            (
                item
                for item in sections
                if source_anchor_matches_section(target.outcome_anchor, item, routed_paths)
            ),
            None,
        )
        if section is None:
            raise CanvasGenerationRepairableError(
                f"Practice target {target.id} has no section containing its validated source anchor for the outcome."
            )
        assignments[section.id].append(target)
    return {section_id: tuple(targets) for section_id, targets in assignments.items()}


def practice_source_sections(source_document: CanvasDocument) -> list[CanvasSection]:
    return group_evidence_sections(
        source_topic_sections(source_document) or source_document.sections,
        document_source_ref=source_document.source_ref,
    )


def validate_section_practice(section: CanvasSection, targets: Sequence[PracticeTarget]) -> None:
    expected = {f"practice-{target.id}": target for target in targets}
    canonical = [block for block in section.blocks if block.id.startswith("practice-")]
    if any(block.id not in expected for block in canonical):
        raise CanvasGenerationRepairableError(
            "Section contains a practice checkpoint assigned to different source evidence.",
            section_id=section.id,
        )
    for checkpoint_id, target in expected.items():
        matches = [block for block in canonical if block.id == checkpoint_id]
        if (
            len(matches) != 1
            or matches[0].type != "checkpoint"
            or matches[0].text != target.baseline_task
        ):
            raise CanvasGenerationRepairableError(
                f"Section needs exactly one {checkpoint_id} checkpoint with the exact approved baseline task.",
                section_id=section.id,
            )


def validate_practice_candidate(
    document: CanvasDocument,
    design: PracticeDesign,
    *,
    source_document: CanvasDocument | None = None,
) -> None:
    try:
        expected_source_sections = None
        if source_document is not None:
            source_sections = practice_source_sections(source_document)
            assignments = section_target_assignments(design, source_sections)
            expected_source_sections = {
                target.id: section.id
                for section in source_sections
                for target in assignments[section.id]
            }
        validate_canvas_practice_contract(
            document,
            design,
            expected_source_sections=expected_source_sections,
        )
    except PracticeDesignValidationError as exc:
        raise CanvasGenerationRepairableError(str(exc), candidate=document) from exc
