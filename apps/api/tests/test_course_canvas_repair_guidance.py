from lecturepilot.course_canvas_repair_guidance import repair_guidance


def test_repair_guidance_selects_only_relevant_bounded_examples() -> None:
    guidance = repair_guidance(
        "The claim is unsupported by the supplied evidence. "
        "The displayed formula has inconsistent sample indexing. "
        "The checkpoint depends on an omitted table."
    )

    assert "Edit only the requested blocks" in guidance
    assert "remove the unsupported consequence" in guidance
    assert "preserve every source variable and index" in guidance
    assert "restated inside the task" not in guidance
    assert guidance.count("Before:") == 2


def test_repair_guidance_teaches_self_contained_assessment_repairs() -> None:
    guidance = repair_guidance("The checkpoint depends on an omitted distance matrix.")

    assert "restated inside the task" in guidance
    assert "Do not invent missing values" in guidance
