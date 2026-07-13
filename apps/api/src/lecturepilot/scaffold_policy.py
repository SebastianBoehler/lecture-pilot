from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

GuidanceLevel = Literal["challenge", "standard", "scaffolded"]
RevisionTaskKind = Literal["review_wrong_mc", "review_open_answer"]
LearnerStage = Literal["novice", "early_intermediate", "late_intermediate"]
ScaffoldTrigger = Literal[
    "readiness_task",
    "conceptual",
    "procedural",
    "error",
    "delayed_transfer",
]
ScaffoldProfile = Literal["worked_example", "faded_example", "self_explanation", "transfer"]
ProcessLabel = Literal[
    "shallow_lookup", "scaffolded_reasoning", "self_explanation", "transfer_attempt"
]


class TutorScaffoldPolicy(BaseModel):
    trigger: ScaffoldTrigger
    learner_stage: LearnerStage
    profile: ScaffoldProfile
    process_label: ProcessLabel
    tutor_move: str = Field(min_length=1, max_length=500)
    forbidden: str = Field(min_length=1, max_length=500)


def scaffold_policy_for_revision_task(
    *,
    guidance_level: GuidanceLevel,
    task_kind: RevisionTaskKind,
) -> TutorScaffoldPolicy:
    if guidance_level == "scaffolded":
        return TutorScaffoldPolicy(
            trigger="readiness_task",
            learner_stage="novice",
            profile="worked_example",
            process_label="scaffolded_reasoning",
            tutor_move=(
                "Show one source-grounded worked example step, explain why it works, "
                "then ask the learner to complete the next step."
            ),
            forbidden="Do not ask for a full independent solution before giving the worked step.",
        )
    if guidance_level == "challenge":
        return TutorScaffoldPolicy(
            trigger="readiness_task",
            learner_stage="late_intermediate",
            profile="transfer",
            process_label="transfer_attempt",
            tutor_move=(
                "Ask a transfer question with minimal hints and provide corrective feedback "
                "only after the learner attempts it."
            ),
            forbidden="Do not reteach the full concept before the learner makes a transfer attempt.",
        )
    if task_kind == "review_open_answer":
        return TutorScaffoldPolicy(
            trigger="readiness_task",
            learner_stage="early_intermediate",
            profile="self_explanation",
            process_label="self_explanation",
            tutor_move="Prompt the learner to compare their answer with the rubric and explain the missing principle.",
            forbidden="Do not rewrite the whole answer before the learner self-explains the gap.",
        )
    return TutorScaffoldPolicy(
        trigger="readiness_task",
        learner_stage="early_intermediate",
        profile="faded_example",
        process_label="self_explanation",
        tutor_move="Give the first reasoning step and leave the next step for the learner to complete.",
        forbidden="Do not reveal the final answer before the learner fills the faded step.",
    )


def scaffold_policy_for_tutor_turn(
    *,
    attendance: str,
    delayed_transfer_due: bool,
    last_gate_status: str | None,
    needs_evidence_count: int,
    prior_assistance: bool,
) -> TutorScaffoldPolicy:
    if delayed_transfer_due:
        return TutorScaffoldPolicy(
            trigger="delayed_transfer",
            learner_stage="late_intermediate",
            profile="transfer",
            process_label="transfer_attempt",
            tutor_move=(
                "Ask one new application question without hints and wait for the learner's "
                "independent attempt before giving corrective feedback."
            ),
            forbidden="Do not provide a hint, solution step, or answer before the delayed attempt.",
        )
    if last_gate_status == "passed":
        return _transfer_policy()
    if needs_evidence_count >= 2:
        return _worked_step_policy(trigger="error")
    if needs_evidence_count == 1:
        return TutorScaffoldPolicy(
            trigger="error",
            learner_stage="early_intermediate",
            profile="faded_example",
            process_label="self_explanation",
            tutor_move="Give one targeted cue or first reasoning step, then leave the next step to the learner.",
            forbidden="Do not reveal the final answer before the learner completes the faded step.",
        )
    if not prior_assistance and attendance == "absent":
        return _worked_step_policy(trigger="conceptual")
    return TutorScaffoldPolicy(
        trigger="conceptual",
        learner_stage="early_intermediate",
        profile="self_explanation",
        process_label="self_explanation",
        tutor_move=(
            "Ask for the learner's own attempt, prediction, or approach, then respond to the "
            "specific evidence they provide."
        ),
        forbidden="Do not solve the whole task before the learner makes an attempt.",
    )


def _worked_step_policy(*, trigger: ScaffoldTrigger) -> TutorScaffoldPolicy:
    return TutorScaffoldPolicy(
        trigger=trigger,
        learner_stage="novice",
        profile="worked_example",
        process_label="scaffolded_reasoning",
        tutor_move=(
            "Model one source-grounded reasoning step, explain the judgment behind it, "
            "then hand the next step to the learner."
        ),
        forbidden="Do not complete the remaining reasoning steps for the learner.",
    )


def _transfer_policy() -> TutorScaffoldPolicy:
    return TutorScaffoldPolicy(
        trigger="conceptual",
        learner_stage="late_intermediate",
        profile="transfer",
        process_label="transfer_attempt",
        tutor_move="Ask one unfamiliar transfer question with no initial hints.",
        forbidden="Do not reteach the concept before the learner attempts the transfer.",
    )
