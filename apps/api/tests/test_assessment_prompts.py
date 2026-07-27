from lecturepilot.assessment_prompts import assessment_prompt_issue


def test_checkpoint_accepts_create_as_a_concrete_task_after_context() -> None:
    prompt = (
        "For the supplied selection-sort implementation, create a variable table for "
        "`arr`, `n`, `i`, `min_idx`, `j`, and `temp`."
    )

    assert assessment_prompt_issue(prompt, "checkpoint") is None


def test_contextual_task_detection_has_no_character_limit() -> None:
    prompt = f"Given {'a detailed source-backed premise ' * 30}, design a valid test case."

    assert assessment_prompt_issue(prompt, "checkpoint") is None
