from authoring_test_helpers import current_draft, fix_math, install_author, markdown
from auth_helpers import professor_headers
from approved_practice_design_helpers import revised_design, store_design
from lecturepilot.learning_design.course_practice_design_store import PracticeDesignStore
from lecturepilot.llm.model_client import ModelExecutionError
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


def test_transient_repair_failure_retains_files_and_resumes_history(tmp_path, monkeypatch):
    client, path = setup_failed_job(tmp_path)

    def interrupted(messages, info):
        raise ModelExecutionError("Connection interrupted")

    install_author(client, monkeypatch, interrupted, Reviewer())
    failed = client.post(path + "/repair", headers=headers("transient-repair-0001"))
    assert failed.status_code == 502, failed.text

    install_author(client, monkeypatch, fix_math, Reviewer())
    repaired = client.post(path + "/repair", headers=headers("resumed-repair-0001"))
    assert repaired.status_code == 200, repaired.text
    assert (
        next(b for b in repaired.json()["sections"][0]["blocks"] if b["id"] == "optimization-math")[
            "text"
        ]
        == r"w^\top x"
    )


def test_quality_feedback_gets_one_targeted_repair_without_a_second_review(tmp_path, monkeypatch):
    client, path = setup_failed_job(tmp_path)
    reviews = []
    repairs = []

    class Critic:
        async def complete_review(self, **kwargs):
            reviews.append([section.id for section in kwargs["candidate_document"].sections])
            return {
                "issues": [
                    {
                        "section_id": "learning-optimization",
                        "block_id": "optimization-math",
                        "reason": "Use x as the source-backed expression.",
                    }
                ]
            }

    def respond(messages, info):
        if "source-backed expression" in str(messages[0].parts[-1].content):
            repairs.append(messages)
            return markdown(current_draft(messages).replace(r"w^\top x", "x"))
        return fix_math(messages, info)

    install_author(client, monkeypatch, respond, Critic())
    repaired = client.post(path + "/repair", headers=headers("quality-repair-0001"))
    assert repaired.status_code == 200, repaired.text
    # One critic call over the whole lecture, one repair, and no re-review of the repair.
    assert len(reviews) == 1 and "learning-optimization" in reviews[0] and len(reviews[0]) > 1
    assert len(repairs) == 1
    assert any("repaired once, not re-checked" in w for w in repaired.json()["warnings"])


def test_completed_repair_replays_without_another_model_request(tmp_path, monkeypatch):
    client, path = setup_failed_job(tmp_path)
    calls = 0

    def respond(messages, info):
        nonlocal calls
        calls += 1
        return fix_math(messages, info)

    install_author(client, monkeypatch, respond, Reviewer())
    request_headers = headers("idempotent-repair-0001")
    first = client.post(path + "/repair", headers=request_headers)
    second = client.post(path + "/repair", headers=request_headers)
    assert first.status_code == second.status_code == 200, first.text
    assert first.json() == second.json()
    assert calls == 1


def test_approved_design_conflict_replays_as_review_required(tmp_path):
    from lecturepilot.authoring.authoring_models import AuthoringDesignConflict

    client, path = setup_failed_job(tmp_path)
    layout = client.app.state.canvas_workspace.layout
    current = PracticeDesignStore(layout).read(course_id="targeted-repair", lecture_id="lecture-01")
    # Every task is professor-fixed (e.g. a migrated full approval): AI repair cannot help.
    store_design(layout, revised_design(current, fixed=True))

    class ConflictingAuthor:
        async def plan_canvas(self, source, **kwargs):
            raise AuthoringDesignConflict("Review the approved practice design.")

    client.app.state.course_planner = ConflictingAuthor()
    request_headers = headers("design-conflict-0001")
    first = client.post(path, headers=request_headers)
    replay = client.post(path, headers=request_headers)
    assert first.status_code == replay.status_code == 409
