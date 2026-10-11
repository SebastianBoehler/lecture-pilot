from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)

from lecturepilot.teaching_history import compact_teaching_history


def prompt(source, state):
    return ModelRequest(
        parts=[
            UserPromptPart(
                source + "\nApproved read-only intent:\nintent" + "\nCurrent target IDs: " + state
            )
        ]
    )


def test_resume_keeps_latest_context_and_review_without_changing_saved_history():
    old, latest = prompt("same-source", "old"), prompt("same-source", "new")
    messages = [
        old,
        ModelResponse(parts=[ToolCallPart("validate", {}, tool_call_id="a")]),
        ModelRequest(parts=[ToolReturnPart("validate", {"valid": False}, tool_call_id="a")]),
        latest,
        ModelResponse(parts=[ToolCallPart("validate", {}, tool_call_id="b")]),
        ModelRequest(parts=[ToolReturnPart("validate", {"valid": True}, tool_call_id="b")]),
    ]
    compacted = compact_teaching_history(messages)
    assert compacted[0].parts[0].content != old.parts[0].content
    assert compacted[3].parts[0].content == latest.parts[0].content
    assert compacted[2].parts[0].content != messages[2].parts[0].content
    assert compacted[2].parts[0].tool_call_id == "a"
    assert compacted[-1].parts[0].content == {"valid": True}
    assert messages[2].parts[0].content == {"valid": False}
    assert "same-source" in old.parts[0].content


def test_changed_source_context_and_unrelated_prompts_are_preserved():
    messages = [
        prompt("old-source", "old"),
        prompt("new-source", "new"),
        ModelRequest(parts=[UserPromptPart("Keep this separate instruction.")]),
    ]
    compacted = compact_teaching_history(messages)
    assert compacted == messages


def test_pending_validate_does_not_remove_latest_completed_review():
    messages = [
        ModelResponse(parts=[ToolCallPart("validate", {}, tool_call_id="a")]),
        ModelRequest(parts=[ToolReturnPart("validate", {"valid": False}, tool_call_id="a")]),
        ModelResponse(parts=[ToolCallPart("validate", {}, tool_call_id="b")]),
    ]
    assert compact_teaching_history(messages) == messages
