from __future__ import annotations

import json
from collections.abc import Sequence

from lecturepilot.canvas_models import CanvasDocument, CanvasSection
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_practice_design_models import PracticeDesign, PracticeTarget
from lecturepilot.course_practice_design_validation import (
    PracticeDesignValidationError,
    validate_canvas_practice_contract,
)


def practice_prompt_instruction(
    design: PracticeDesign, *, targets: Sequence[PracticeTarget] | None = None
) -> str:
    scoped = tuple(targets) if targets is not None else design.targets
    expected = [f"practice-{target.id}" for target in design.targets]
    contracts = [
        {
            "checkpoint_id": f"practice-{target.id}",
            "baseline_task": target.baseline_task,
            "evidence_criteria": [
                {"id": criterion.id, "description": criterion.description}
                for criterion in target.evidence_criteria
            ],
            "source_refs": target.source_refs,
        }
        for target in scoped
    ]
    return (
        f"Approved practice-design revision: {design.revision}. The lecture must contain exactly "
        f"one checkpoint for each canonical id {json.dumps(expected)} and no other practice-* "
        "checkpoint. Each canonical checkpoint text must exactly equal its approved baseline_task; "
        "do not paraphrase, split, merge, duplicate, or move it into another block type. "
        f"Applicable approved target contracts: {json.dumps(contracts)}"
    )


def section_target_assignments(
    design: PracticeDesign, sections: Sequence[CanvasSection]
) -> dict[str, tuple[PracticeTarget, ...]]:
    assignments: dict[str, list[PracticeTarget]] = {section.id: [] for section in sections}
    for target in design.targets:
        section = next((item for item in sections if _matches(target, item)), sections[0])
        assignments[section.id].append(target)
    return {section_id: tuple(targets) for section_id, targets in assignments.items()}


def validate_practice_candidate(document: CanvasDocument, design: PracticeDesign) -> None:
    try:
        validate_canvas_practice_contract(document, design)
    except PracticeDesignValidationError as exc:
        raise CanvasGenerationRepairableError(str(exc), candidate=document) from exc


def _matches(target: PracticeTarget, section: CanvasSection) -> bool:
    source_ref = (section.source_ref or "").casefold()
    return any(path.casefold() in source_ref for path in target.source_refs)
