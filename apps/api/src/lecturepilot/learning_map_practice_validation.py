from __future__ import annotations

from typing import Protocol
from lecturepilot.course_practice_design_models import PracticeDesign
from lecturepilot.course_practice_design_validation import PracticeDesignValidationError
from lecturepilot.practice_task_bank import SupplementalPracticeTask


class _LearningMapCriterion(Protocol):
    id: str
    description: str
    required: bool


class _LearningMapMisconception(Protocol):
    id: str
    description: str
    diagnostic_cue: str


class _LearningMapHint(Protocol):
    level: str
    content: str
    evidence_ids: list[str]


class _LearningMapGate(Protocol):
    id: str
    practice_target_id: str | None
    prompt: str
    target_invariant: str | None
    evidence_criteria: list[_LearningMapCriterion]
    transfer_prompt: str
    independent_exit_task: str | None
    independent_exit_surface_change: str | None
    delayed_transfer_surface_change: str | None
    misconceptions: list[_LearningMapMisconception]
    hint_ladder: list[_LearningMapHint]
    supplemental_tasks: list[SupplementalPracticeTask]
    review_after_days: int


class _LearningMap(Protocol):
    objective: str
    gates: list[_LearningMapGate]


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
        expected_criteria = [
            {
                "id": item.id,
                "description": item.description,
                "required": item.required,
            }
            for item in target.evidence_criteria
        ]
        observed_criteria = [
            {"id": item.id, "description": item.description, "required": item.required}
            for item in gate.evidence_criteria
        ]
        expected_misconceptions = [
            {
                "id": item.id,
                "description": item.description,
                "diagnostic_cue": item.diagnostic_cue,
            }
            for item in target.misconceptions
        ]
        observed_misconceptions = [
            {
                "id": item.id,
                "description": item.description,
                "diagnostic_cue": item.diagnostic_cue,
            }
            for item in gate.misconceptions
        ]
        expected_hints = [
            {"level": item.level, "content": item.content, "evidence_ids": list(item.evidence_ids)}
            for item in target.hint_ladder
        ]
        observed_hints = [
            {"level": item.level, "content": item.content, "evidence_ids": list(item.evidence_ids)}
            for item in gate.hint_ladder
        ]
        if (
            gate.prompt != target.baseline_task
            or gate.target_invariant != target.target_invariant
            or observed_criteria != expected_criteria
            or gate.independent_exit_task != target.independent_exit_task
            or gate.independent_exit_surface_change != target.independent_exit_surface_change
            or gate.transfer_prompt != target.delayed_transfer_task
            or gate.delayed_transfer_surface_change != target.delayed_transfer_surface_change
            or observed_misconceptions != expected_misconceptions
            or observed_hints != expected_hints
            or tuple(gate.supplemental_tasks) != target.supplemental_tasks
            or gate.review_after_days != target.review_after_days
        ):
            raise PracticeDesignValidationError(
                f"Learning-map gate practice-{target_id} differs from the approved practice target."
            )
