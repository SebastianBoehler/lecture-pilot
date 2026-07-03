from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

GuidanceLevel = Literal["challenge", "standard", "scaffolded"]
RevisionTaskKind = Literal["review_wrong_mc", "review_open_answer"]
LearnerStage = Literal["novice", "early_intermediate", "late_intermediate"]
ScaffoldTrigger = Literal["readiness_task", "conceptual", "procedural", "error"]
ScaffoldProfile = Literal["worked_example", "faded_example", "self_explanation", "transfer"]
ProcessLabel = Literal["shallow_lookup", "scaffolded_reasoning", "self_explanation", "transfer_attempt"]


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
