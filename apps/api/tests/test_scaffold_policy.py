from lecturepilot.scaffold_policy import scaffold_policy_for_revision_task


def test_scaffolded_guidance_uses_worked_examples() -> None:
    policy = scaffold_policy_for_revision_task(
        guidance_level="scaffolded",
        task_kind="review_wrong_mc",
    )

    assert policy.learner_stage == "novice"
    assert policy.profile == "worked_example"
    assert policy.process_label == "scaffolded_reasoning"


def test_standard_wrong_mc_uses_faded_example() -> None:
    policy = scaffold_policy_for_revision_task(
        guidance_level="standard",
        task_kind="review_wrong_mc",
    )

    assert policy.learner_stage == "early_intermediate"
    assert policy.profile == "faded_example"


def test_standard_open_answer_uses_self_explanation() -> None:
    policy = scaffold_policy_for_revision_task(
        guidance_level="standard",
        task_kind="review_open_answer",
    )

    assert policy.profile == "self_explanation"
    assert "rubric" in policy.tutor_move


def test_challenge_guidance_uses_transfer_attempt() -> None:
    policy = scaffold_policy_for_revision_task(
        guidance_level="challenge",
        task_kind="review_open_answer",
    )

    assert policy.learner_stage == "late_intermediate"
    assert policy.profile == "transfer"
    assert policy.process_label == "transfer_attempt"
