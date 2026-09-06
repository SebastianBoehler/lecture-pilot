from pydantic_ai.messages import ModelResponse, ToolCallPart

from authoring_test_helpers import assigned_drafts, install_author
from lecturepilot.model_client import ModelExecutionError
from test_course_canvas_targeted_repair import _course_client
from test_course_canvas_targeted_repair_resilience import Reviewer, headers


def test_fresh_agent_failure_and_failed_retry_keep_one_durable_session(tmp_path, monkeypatch):
    client = _course_client(tmp_path)
    path = "/admin/courses/targeted-repair/lectures/lecture-01/canvas/draft"
    calls = 0

    def interrupted(messages, info):
        nonlocal calls
        calls += 1
        if calls == 1:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        "write",
                        {
                            "path": draft,
                            "text": (
                                f'# Inner product\n<!-- block id="explain-{index}" type="paragraph" -->\n'
                                "The weight and input vectors must have matching dimensions for the inner product.\n\n"
                                f'<!-- block id="check-{index}" type="checkpoint" -->\n'
                                ":::checkpoint Apply it\nExplain why the vector dimensions must match.\n:::\n"
                            ),
                        },
                    )
                    for index, draft in enumerate(assigned_drafts(info))
                ]
            )
        raise ModelExecutionError("Provider connection interrupted")

    install_author(client, monkeypatch, interrupted, Reviewer())
    first = client.post(path, headers=headers("native-failure-0001"))
    assert first.status_code == 502, first.text
    assert first.headers.get("X-Generation-Repairable") == "true"
    restored = client.get(path, headers=headers("native-failure-0001"))
    assert restored.status_code == 404
    assert restored.headers.get("X-Generation-Repairable") == "true"
    retry = client.post(path + "/repair", headers=headers("native-failure-0002"))
    assert retry.status_code == 502, retry.text
    assert retry.headers.get("X-Generation-Repairable") == "true"

    def resumed(messages, info):
        assert any(
            getattr(part, "tool_name", None) == "write"
            for message in messages
            for part in message.parts
        )
        return ModelResponse(parts=[ToolCallPart("final_result", {"ready": True})])

    install_author(client, monkeypatch, resumed, Reviewer())
    result = client.post(path + "/repair", headers=headers("native-success-0003"))
    assert result.status_code == 200, result.text
    status = client.get(path + "/status", headers=headers("native-success-0003"))
    assert status.json()["authoring_metrics"]["resumes"] == 2
