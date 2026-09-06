from pydantic_ai.messages import ModelResponse, ToolCallPart

from authoring_test_helpers import assigned_drafts, install_author
from auth_helpers import professor_headers
from lecturepilot.model_client import ModelExecutionError
from test_course_canvas_targeted_repair import (
    _TargetedRepairPlanner,
    _client_contract_headers,
    _course_client,
)


def setup_failed_job(tmp_path):
    client = _course_client(tmp_path)
    client.app.state.course_planner = _TargetedRepairPlanner()
    path = "/admin/courses/targeted-repair/lectures/lecture-01/canvas/draft"
    failed = client.post(path, headers=headers("initial-failure-0001"))
    assert failed.status_code == 503
    return client, path


def headers(key):
    return {**professor_headers(), **_client_contract_headers(), "Idempotency-Key": key}


class Reviewer:
    async def complete_review(self, **kwargs):
        return {"issues": []}


def math_edit(info):
    return ToolCallPart(
        "edit",
        {
            "path": assigned_drafts(info)[0],
            "old": r"The score is computed as w^\top x.",
            "new": r"w^\top x",
        },
    )


def test_transient_repair_failure_retains_files_and_resumes_history(tmp_path, monkeypatch):
    client, path = setup_failed_job(tmp_path)
    calls = 0

    def interrupted(messages, info):
        nonlocal calls
        calls += 1
        if calls == 1:
            return ModelResponse(parts=[math_edit(info)])
        raise ModelExecutionError("Connection interrupted")

    install_author(client, monkeypatch, interrupted, Reviewer())
    failed = client.post(path + "/repair", headers=headers("transient-repair-0001"))
    assert failed.status_code == 502, failed.text

    def resumed(messages, info):
        assert any(
            getattr(part, "tool_name", None) == "edit"
            for message in messages
            for part in message.parts
        )
        return ModelResponse(parts=[ToolCallPart("final_result", {"ready": True})])

    install_author(client, monkeypatch, resumed, Reviewer())
    repaired = client.post(path + "/repair", headers=headers("resumed-repair-0001"))
    assert repaired.status_code == 200, repaired.text
    assert (
        next(b for b in repaired.json()["sections"][0]["blocks"] if b["id"] == "optimization-math")[
            "text"
        ]
        == r"w^\top x"
    )


def test_quality_feedback_is_repaired_in_same_agent_history(tmp_path, monkeypatch):
    client, path = setup_failed_job(tmp_path)
    review_calls = 0

    class Critic:
        async def complete_review(self, **kwargs):
            nonlocal review_calls
            review_calls += 1
            return {
                "issues": (
                    [
                        {
                            "section_id": "learning-optimization",
                            "block_id": "optimization-math",
                            "reason": "Use x as the source-backed expression.",
                        }
                    ]
                    if review_calls == 1
                    else []
                )
            }

    calls = 0

    def respond(messages, info):
        nonlocal calls
        calls += 1
        if calls == 1:
            return ModelResponse(parts=[math_edit(info)])
        if calls == 2:
            return ModelResponse(parts=[ToolCallPart("validate", {})])
        if calls == 3:
            assert any(
                "source-backed expression" in str(getattr(p, "content", ""))
                for m in messages
                for p in m.parts
            )
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        "edit", {"path": assigned_drafts(info)[0], "old": r"w^\top x", "new": "x"}
                    )
                ]
            )
        return ModelResponse(parts=[ToolCallPart("final_result", {"ready": True})])

    install_author(client, monkeypatch, respond, Critic())
    repaired = client.post(path + "/repair", headers=headers("quality-repair-0001"))
    assert repaired.status_code == 200, repaired.text
    assert review_calls == 2


def test_completed_repair_replays_without_another_model_request(tmp_path, monkeypatch):
    client, path = setup_failed_job(tmp_path)
    calls = 0

    def respond(messages, info):
        nonlocal calls
        calls += 1
        return ModelResponse(
            parts=[math_edit(info)]
            if calls == 1
            else [ToolCallPart("final_result", {"ready": True})]
        )

    install_author(client, monkeypatch, respond, Reviewer())
    request_headers = headers("idempotent-repair-0001")
    first = client.post(path + "/repair", headers=request_headers)
    second = client.post(path + "/repair", headers=request_headers)
    assert first.status_code == second.status_code == 200, first.text
    assert first.json() == second.json()
    assert calls == 2


def test_approved_design_conflict_replays_as_review_required(tmp_path):
    from lecturepilot.authoring_models import AuthoringDesignConflict

    client, path = setup_failed_job(tmp_path)

    class ConflictingAuthor:
        async def plan_canvas(self, source, **kwargs):
            raise AuthoringDesignConflict("Review the approved practice design.")

    client.app.state.course_planner = ConflictingAuthor()
    request_headers = headers("design-conflict-0001")
    first = client.post(path, headers=request_headers)
    replay = client.post(path, headers=request_headers)
    assert first.status_code == replay.status_code == 409
