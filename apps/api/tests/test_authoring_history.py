from pydantic_ai.messages import ModelRequest, ModelResponse, ToolCallPart, ToolReturnPart

from lecturepilot.authoring_state import AuthoringState, read_state, save_state, resume_messages
from lecturepilot.authoring_history import compact_authoring_history


def messages():
    return [
        ModelResponse(
            parts=[ToolCallPart("read", {"path": "/evidence/topic.md"}, tool_call_id="a")]
        ),
        ModelRequest(
            parts=[ToolReturnPart("read", {"text": "first", "next_offset": None}, tool_call_id="a")]
        ),
        ModelResponse(
            parts=[ToolCallPart("read", {"path": "/evidence/topic.md"}, tool_call_id="b")]
        ),
        ModelRequest(
            parts=[
                ToolReturnPart("read", {"text": "latest", "next_offset": None}, tool_call_id="b")
            ]
        ),
    ]


def test_compaction_keeps_latest_evidence_and_tool_pairs():
    original = messages()
    compacted = compact_authoring_history(original)
    assert compacted[1].parts[0].tool_call_id == "a"
    assert compacted[1].parts[0].content != original[1].parts[0].content
    assert compacted[-1].parts[0].content == original[-1].parts[0].content
    assert original[1].parts[0].content["text"] == "first"


def test_incremental_history_keeps_sealed_messages_out_of_session(tmp_path):
    import json

    state = AuthoringState(identity="same")
    history = messages()
    save_state(tmp_path, state, history[:2])
    save_state(tmp_path, state, history)
    payload = json.loads((tmp_path / "session.json").read_text())
    assert payload["history_count"] == 2
    assert len(payload["messages"]) == 2
    restored = read_state(tmp_path)
    assert resume_messages(restored) == history
    sealed = tmp_path / "history/00000000.json"
    before = sealed.stat().st_mtime_ns
    save_state(tmp_path, state, history)
    assert sealed.stat().st_mtime_ns == before
