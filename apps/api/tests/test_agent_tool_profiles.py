from lecturepilot.agent_tool_schemas import (
    agent_tool_names,
    agent_tool_schemas,
    tutor_tool_profile_for_message,
)


def test_agent_tool_profiles_expose_minimal_expected_tools() -> None:
    tutor = agent_tool_names("tutor")
    evidence = agent_tool_names("evidence")
    course_builder = agent_tool_names("course_builder")

    assert {"find", "grep"}.isdisjoint(tutor)
    assert {"find", "grep"}.issubset(evidence)
    assert "remember" in tutor
    assert {"record_gate", "remember", "focus", "highlight"}.isdisjoint(course_builder)
    assert {
        "pwd",
        "ls",
        "find",
        "grep",
        "read",
        "write",
        "edit",
        "generate_image",
    } == course_builder
    assert {schema["function"]["name"] for schema in agent_tool_schemas("tutor")} == tutor
    assert tutor_tool_profile_for_message("show me the exact source for this claim") == "evidence"
    assert tutor_tool_profile_for_message("help me understand this formula") == "tutor"
