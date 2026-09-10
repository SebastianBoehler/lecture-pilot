from __future__ import annotations

from dataclasses import dataclass
from typing import Collection

from lecturepilot.coaching_assistance import NextCheck, NextCheckAssistance
from lecturepilot.coaching_task_bank import canonical_task_id, task_ids_for_stage, task_prompt
from lecturepilot.coaching_contract import AssessmentStage
from lecturepilot.coaching_state_models import AssessedAttemptKind
from lecturepilot.learning_map import LearningMapGate
from lecturepilot.quality_gate_models import QualityGateStatus


@dataclass(frozen=True)
class CheckTransition:
    stage: AssessmentStage
    check: NextCheck
    task_id: str | None = None
    bank_exhausted: bool = False


def initial_assessment_stage(gate: LearningMapGate) -> AssessmentStage:
    return "diagnostic" if gate.practice_target_id is not None else "independent_exit"


def derive_next_transition(
    gate: LearningMapGate,
    *,
    current_stage: AssessmentStage,
    status: QualityGateStatus,
    exposed_hint_levels: Collection[str],
    exposed_task_ids: Collection[str] = (),
    current_task_id: str | None = None,
    missing_evidence_ids: Collection[str] = (),
) -> CheckTransition | None:
    if set(missing_evidence_ids) - {item.id for item in gate.evidence_criteria}:
        raise ValueError("Unknown missing evidence IDs.")
    task_id = current_task_id or canonical_task_id(current_stage)
    if status == QualityGateStatus.PASSED:
        transition = _passed_transition(gate, current_stage)
        if transition is None:
            return None
        candidates = task_ids_for_stage(gate, transition.stage)
        fresh = next((item for item in candidates if item not in exposed_task_ids), None)
        if fresh is not None:
            return CheckTransition(
                stage=transition.stage,
                task_id=fresh,
                check=_check(
                    gate,
                    prompt=task_prompt(gate, fresh),
                    assistance=NextCheckAssistance(level="none", content=None),
                ),
            )
        return CheckTransition(
            stage=_support_stage(current_stage),
            task_id=task_id,
            bank_exhausted=True,
            check=_check(
                gate,
                prompt=task_prompt(gate, task_id),
                assistance=_next_assistance(gate, exposed_hint_levels, missing_evidence_ids),
            ),
        )
    base_stage = "delayed_transfer" if current_stage.startswith("delayed") else "independent_exit"
    exhausted = not current_stage.startswith("diagnostic") and not any(
        item not in exposed_task_ids for item in task_ids_for_stage(gate, base_stage)
    )
    return CheckTransition(
        stage=_support_stage(current_stage),
        task_id=task_id,
        bank_exhausted=exhausted,
        check=_check(
            gate,
            prompt=task_prompt(gate, task_id),
            assistance=_next_assistance(gate, exposed_hint_levels, missing_evidence_ids),
        ),
    )


def attempt_kind_for_stage(stage: AssessmentStage) -> AssessedAttemptKind:
    if stage == "diagnostic":
        return "diagnostic"
    if stage == "independent_exit":
        return "independent_exit"
    if stage == "delayed_transfer":
        return "delayed_transfer"
    return "supported_retry"


def prompt_for_stage(gate: LearningMapGate, stage: AssessmentStage) -> str:
    return _prompt_for_stage(gate, stage)


def _passed_transition(
    gate: LearningMapGate, current_stage: AssessmentStage
) -> CheckTransition | None:
    if current_stage in {"diagnostic", "diagnostic_support", "exit_support"}:
        stage: AssessmentStage = "independent_exit"
        return CheckTransition(
            stage=stage,
            check=_check(
                gate,
                prompt=_prompt_for_stage(gate, stage),
                assistance=NextCheckAssistance(level="none", content=None),
            ),
        )
    if current_stage == "delayed_support":
        return CheckTransition(
            stage="delayed_transfer",
            check=_check(
                gate,
                prompt=gate.transfer_prompt,
                assistance=NextCheckAssistance(level="none", content=None),
            ),
        )
    return None


def _support_stage(current_stage: AssessmentStage) -> AssessmentStage:
    if current_stage in {"diagnostic", "diagnostic_support"}:
        return "diagnostic_support"
    if current_stage in {"independent_exit", "exit_support"}:
        return "exit_support"
    return "delayed_support"


def _prompt_for_stage(gate: LearningMapGate, stage: AssessmentStage) -> str:
    if stage in {"diagnostic", "diagnostic_support"}:
        return gate.prompt
    if stage in {"independent_exit", "exit_support"}:
        return gate.independent_exit_task or gate.prompt
    return gate.transfer_prompt


def _next_assistance(
    gate: LearningMapGate,
    exposed_hint_levels: Collection[str],
    missing_evidence_ids: Collection[str],
) -> NextCheckAssistance:
    exposed = set(exposed_hint_levels)
    missing = set(missing_evidence_ids)
    available = [item for item in gate.hint_ladder if item.level not in exposed]
    targeted = [item for item in available if missing.intersection(item.evidence_ids)]
    general = [item for item in available if not item.evidence_ids]
    hint = next(iter(targeted or general), None)
    if hint is None:
        return NextCheckAssistance(level="none", content=None)
    return NextCheckAssistance(level=hint.level, content=hint.content)


def _check(
    gate: LearningMapGate,
    *,
    prompt: str,
    assistance: NextCheckAssistance,
) -> NextCheck:
    return NextCheck(
        gate_id=gate.id,
        gate_revision=gate.revision,
        prompt=prompt,
        assistance=assistance,
    )
