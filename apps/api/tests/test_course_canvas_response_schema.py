from lecturepilot.agent_response_schema import course_canvas_response_format


def test_course_canvas_schema_requires_answered_quizzes() -> None:
    schema = course_canvas_response_format()["json_schema"]["schema"]
    variants = schema["properties"]["sections"]["items"]["properties"]["blocks"]["items"]["anyOf"]

    quiz = next(
        variant
        for variant in variants
        if variant["properties"].get("type", {}).get("const") == "quiz"
    )

    assert quiz["properties"]["items"]["minItems"] == 2
    assert quiz["properties"]["answer_index"]["type"] == "integer"


def test_course_canvas_schema_rejects_incomplete_single_choice_components() -> None:
    schema = course_canvas_response_format()["json_schema"]["schema"]
    block_schema = schema["properties"]["sections"]["items"]["properties"]["blocks"]["items"]

    variants = block_schema["anyOf"]
    single_choice = next(
        variant
        for variant in variants
        if variant["properties"].get("component_type", {}).get("const") == "single_choice_quiz"
    )

    assert single_choice["properties"]["type"] == {"type": "string", "const": "component"}
    assert single_choice["properties"]["items"]["minItems"] == 2
    assert single_choice["properties"]["option_ids"]["minItems"] == 2
    assert single_choice["properties"]["answer_index"]["type"] == "integer"


def test_course_canvas_schema_requires_component_data_for_visual_components() -> None:
    schema = course_canvas_response_format()["json_schema"]["schema"]
    variants = schema["properties"]["sections"]["items"]["properties"]["blocks"]["items"]["anyOf"]

    for component_type in (
        "interactive_chart",
        "process_explorer",
        "visual_artifact",
        "mechanism_comparison",
    ):
        variant = next(
            item
            for item in variants
            if item["properties"].get("component_type", {}).get("const") == component_type
        )
        assert variant["properties"]["component_data"]["type"] == "object"


def test_course_canvas_schema_bounds_declarative_visual_artifacts() -> None:
    schema = course_canvas_response_format()["json_schema"]["schema"]
    variants = schema["properties"]["sections"]["items"]["properties"]["blocks"]["items"]["anyOf"]
    visual = next(
        item
        for item in variants
        if item["properties"].get("component_type", {}).get("const") == "visual_artifact"
    )

    data = visual["properties"]["component_data"]
    assert data["properties"]["visual_nodes"]["maxItems"] == 12
    assert data["properties"]["visual_series"]["maxItems"] == 6
    assert data["additionalProperties"] is False


def test_course_canvas_schema_does_not_require_null_placeholders() -> None:
    schema = course_canvas_response_format()["json_schema"]["schema"]
    section = schema["properties"]["sections"]["items"]
    variants = section["properties"]["blocks"]["items"]["anyOf"]
    paragraph = next(
        variant
        for variant in variants
        if variant["properties"].get("type", {}).get("const") == "paragraph"
    )

    assert section["required"] == ["title", "blocks"]
    assert paragraph["required"] == ["type", "text"]
    assert set(paragraph["properties"]) == {"type", "text"}
