from lecturepilot.scaffold_policy import (
    scaffold_policy_for_revision_task,
    scaffold_policy_for_tutor_turn,
)


def test_scaffolded_guidance_uses_worked_examples() -> None:
    policy = scaffold_policy_for_revision_task(
        guidance_level="scaffolded",
        task_kind="review_wrong_mc",
    )

    assert policy.learner_stage == "novice"
    assert policy.profile == "worked_example"
    assert policy.process_label == "scaffolded_reasoning"
    assert policy.assistance_level == "worked_step"


def test_standard_wrong_mc_uses_faded_example() -> None:
    policy = scaffold_policy_for_revision_task(
        guidance_level="standard",
        task_kind="review_wrong_mc",
    )

    assert policy.learner_stage == "early_intermediate"
    assert policy.profile == "faded_example"
    assert policy.assistance_level == "faded_example"


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


def test_first_diagnostic_turn_asks_for_self_explanation() -> None:
    policy = scaffold_policy_for_tutor_turn(
        attendance="unknown",
        delayed_transfer_due=False,
        last_gate_status=None,
        needs_evidence_count=0,
        prior_assistance=False,
    )

    assert policy.profile == "self_explanation"
    assert policy.trigger == "conceptual"
    assert policy.assistance_level == "prompt"
    assert "attempt" in policy.tutor_move.lower()


def test_absent_learner_gets_one_worked_step_before_handoff() -> None:
    policy = scaffold_policy_for_tutor_turn(
        attendance="absent",
        delayed_transfer_due=False,
        last_gate_status=None,
        needs_evidence_count=0,
        prior_assistance=False,
    )

    assert policy.profile == "worked_example"
    assert "next step" in policy.tutor_move.lower()


def test_repeated_missing_evidence_escalates_support() -> None:
    policy = scaffold_policy_for_tutor_turn(
        attendance="present",
        delayed_transfer_due=False,
        last_gate_status="needs_evidence",
        needs_evidence_count=2,
        prior_assistance=True,
    )

    assert policy.profile == "worked_example"
    assert policy.assistance_level == "worked_step"


def test_first_missing_evidence_uses_a_targeted_cue() -> None:
    policy = scaffold_policy_for_tutor_turn(
        attendance="present",
        delayed_transfer_due=False,
        last_gate_status="needs_evidence",
        needs_evidence_count=1,
        prior_assistance=True,
    )

    assert policy.profile == "faded_example"
    assert policy.assistance_level == "cue"


def test_passed_gate_and_delayed_check_return_agency() -> None:
    passed = scaffold_policy_for_tutor_turn(
        attendance="present",
        delayed_transfer_due=False,
        last_gate_status="passed",
        needs_evidence_count=0,
        prior_assistance=True,
    )
    delayed = scaffold_policy_for_tutor_turn(
        attendance="present",
        delayed_transfer_due=True,
        last_gate_status="passed",
        needs_evidence_count=0,
        prior_assistance=True,
    )

    assert passed.profile == "transfer"
    assert passed.assistance_level == "none"
    assert delayed.profile == "transfer"
    assert delayed.assistance_level == "none"
    assert delayed.trigger == "delayed_transfer"
    assert "without hints" in delayed.tutor_move.lower()
