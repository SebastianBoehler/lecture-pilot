from __future__ import annotations

from dataclasses import dataclass
from typing import Collection

from lecturepilot.coaching_assistance import NextCheck, NextCheckAssistance
from lecturepilot.coaching_contract import AssessmentStage
from lecturepilot.coaching_state_models import AssessedAttemptKind
from lecturepilot.learning_map import LearningMapGate
from lecturepilot.quality_gate_models import QualityGateStatus


@dataclass(frozen=True)
class CheckTransition:
    stage: AssessmentStage
    check: NextCheck


def initial_assessment_stage(gate: LearningMapGate) -> AssessmentStage:
    return "diagnostic" if gate.practice_target_id is not None else "independent_exit"


def derive_next_transition(
    gate: LearningMapGate,
    *,
    current_stage: AssessmentStage,
    status: QualityGateStatus,
    exposed_hint_levels: Collection[str],
) -> CheckTransition | None:
    if status == QualityGateStatus.PASSED:
        return _passed_transition(gate, current_stage)
    support_stage = _support_stage(current_stage)
    return CheckTransition(
        stage=support_stage,
        check=_check(
            gate,
            prompt=_prompt_for_stage(gate, support_stage),
            assistance=_next_assistance(gate, exposed_hint_levels),
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
    gate: LearningMapGate, exposed_hint_levels: Collection[str]
) -> NextCheckAssistance:
    exposed = set(exposed_hint_levels)
    hint = next((item for item in gate.hint_ladder if item.level not in exposed), None)
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
