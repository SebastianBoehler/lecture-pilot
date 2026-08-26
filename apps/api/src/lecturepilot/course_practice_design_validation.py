from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from lecturepilot.course_practice_design_models import PracticeDesign, PracticeDesignProposal


class PracticeDesignValidationError(ValueError):
    """Raised when a design cannot be grounded in the lecture contract."""


class _CanvasBlock(Protocol):
    id: str
    type: str
    text: str | None


class _CanvasSection(Protocol):
    source_ref: str | None
    blocks: list[_CanvasBlock]


class _CanvasDocument(Protocol):
    sections: list[_CanvasSection]


class _LearningMapCriterion(Protocol):
    id: str
    description: str
    required: bool


class _LearningMapGate(Protocol):
    id: str
    practice_target_id: str | None
    prompt: str
    evidence_criteria: list[_LearningMapCriterion]
    transfer_prompt: str
    review_after_days: int


class _LearningMap(Protocol):
    objective: str
    gates: list[_LearningMapGate]


def validate_practice_design(
    design: PracticeDesign | PracticeDesignProposal, allowed_source_paths: Iterable[str]
) -> None:
    allowed = set(allowed_source_paths)
    for target in design.targets:
        unknown = set(target.source_refs) - allowed
        if unknown:
            paths = ", ".join(sorted(unknown))
            raise PracticeDesignValidationError(
                f"Practice target {target.id} references unrouted source paths: {paths}."
            )


def validate_canvas_practice_contract(document: _CanvasDocument, design: PracticeDesign) -> None:
    """Validate canonical target checkpoints without importing canvas models.

    The document needs sections with ``source_ref`` and blocks with ``id``,
    ``type``, and ``text``. Later canvas contract fields can be checked here
    without making practice-design models depend on the canvas package.
    """

    expected = {target.id: target for target in design.targets}
    checkpoints: dict[str, list[tuple[_CanvasSection, _CanvasBlock]]] = {
        target_id: [] for target_id in expected
    }
    unknown: list[str] = []
    for section in document.sections:
        for block in section.blocks:
            if not block.id.startswith("practice-"):
                continue
            target_id = block.id.removeprefix("practice-")
            if block.type != "checkpoint":
                raise PracticeDesignValidationError(
                    f"Practice block id {block.id} may only be a checkpoint."
                )
            if target_id not in expected:
                unknown.append(target_id)
            else:
                checkpoints[target_id].append((section, block))

    if unknown:
        raise PracticeDesignValidationError(
            f"Canvas claims unknown practice targets: {', '.join(sorted(set(unknown)))}."
        )
    for target_id, target in expected.items():
        matches = checkpoints[target_id]
        if len(matches) != 1:
            raise PracticeDesignValidationError(
                f"Canvas needs exactly one practice-{target_id} checkpoint."
            )
        section, block = matches[0]
        if not section.source_ref:
            raise PracticeDesignValidationError(
                f"Practice checkpoint practice-{target_id} must be in a source-backed section."
            )
        if block.text != target.baseline_task:
            raise PracticeDesignValidationError(
                f"Practice checkpoint practice-{target_id} must use the approved baseline task."
            )


def validate_learning_map_practice_contract(
    learning_map: _LearningMap, design: PracticeDesign
) -> None:
    if learning_map.objective != design.objective:
        raise PracticeDesignValidationError(
            "Learning-map objective must match the approved practice design."
        )
    expected = {target.id: target for target in design.targets}
    gates: dict[str, list[_LearningMapGate]] = {target_id: [] for target_id in expected}
    for gate in learning_map.gates:
        target_id = gate.practice_target_id
        if target_id is None:
            continue
        if target_id not in expected or gate.id != f"practice-{target_id}":
            raise PracticeDesignValidationError(
                "Learning-map gates must use exact approved practice target IDs."
            )
        gates[target_id].append(gate)
    for target_id, target in expected.items():
        matches = gates[target_id]
        if len(matches) != 1:
            raise PracticeDesignValidationError(
                f"Learning map needs exactly one practice-{target_id} gate."
            )
        gate = matches[0]
        expected_criteria = [item.model_dump() for item in target.evidence_criteria]
        observed_criteria = [
            {"id": item.id, "description": item.description, "required": item.required}
            for item in gate.evidence_criteria
        ]
        if (
            gate.prompt != target.baseline_task
            or observed_criteria != expected_criteria
            or gate.transfer_prompt != target.delayed_transfer_task
            or gate.review_after_days != target.review_after_days
        ):
            raise PracticeDesignValidationError(
                f"Learning-map gate practice-{target_id} differs from the approved practice target."
            )
