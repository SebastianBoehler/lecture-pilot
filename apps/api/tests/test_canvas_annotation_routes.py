import json
from auth_helpers import professor_headers, student_headers
from test_learner_lesson_state_routes import _client, COURSE_ID, PREVIEW
from lecturepilot.agent_tool_executor import AgentToolExecutor
from datetime import UTC, datetime
from lecturepilot.coaching_state_models import CoachingProgress, PendingCheck
from test_learner_lesson_state_routes import _gate, _write_progress

URL = f"/courses/{COURSE_ID}/lectures/lecture-open/annotations"


def test_tool_saves_real_comment_and_http_preserves_ownership(tmp_path):
    client = _client(tmp_path)
    workspace = client.app.state.canvas_workspace
    snapshot = workspace.read_published_canvas_view(
        user_id="student-a", course_id=COURSE_ID, lecture_id="lecture-open"
    )
    block = snapshot.document.sections[0].blocks[0]
    executor = AgentToolExecutor(
        canvas_workspace=workspace,
        course_id=COURSE_ID,
        lecture_id="lecture-open",
        user_id="student-a",
        user_message="Please add an annotation to this passage.",
    )
    result = executor.execute(
        "write",
        {
            "path": "/lecture/annotations/classification.json",
            "content": json.dumps({"block_id": block.id, "comment": "My private learning note."}),
        },
    )
    assert result["ok"] and result["saved"]
    owner = student_headers("student-a", course_ids=[COURSE_ID])
    other = student_headers("student-b", course_ids=[COURSE_ID])
    assert client.get(URL, headers=owner).json()[0]["comment"] == "My private learning note."
    assert client.get(URL, headers=other).json() == []
    read = executor.execute("read", {"path": result["path"]})
    assert read["ok"] and "My private learning note." in read["content"]
    updated = executor.execute(
        "edit",
        {
            "path": result["path"],
            "old_text": "My private learning note.",
            "new_text": "Updated private note.",
        },
    )
    assert updated["ok"] and updated["annotation_id"] == result["annotation_id"]
    saved = client.get(URL, headers=owner).json()
    assert len(saved) == 1 and saved[0]["comment"] == "Updated private note."
    target = f"{URL}/{result['annotation_id']}"
    assert client.delete(target, headers=other).status_code == 404
    assert client.delete(target, headers=owner).status_code == 200
    assert client.get(URL, headers=owner).json() == []
    assert client.get(URL).status_code == 401
    assert client.get(URL, headers=student_headers("outsider", course_ids=[])).status_code == 404
    assert (
        client.get(URL.replace("lecture-open", "lecture-locked"), headers=owner).status_code == 403
    )
    assert client.get(URL, headers=professor_headers("professor")).status_code == 403
    preview = client.get(URL, headers={**professor_headers("professor"), **PREVIEW})
    assert preview.status_code == 200 and preview.json() == []


def test_independent_attempt_hides_comments_and_rejects_annotation_tool(tmp_path):
    client = _client(tmp_path)
    gate = _gate(client, "risk-check")
    progress = CoachingProgress.empty(course_id=COURSE_ID, lecture_id="lecture-open")
    progress.pending_check = PendingCheck(
        gate_id=gate.id,
        gate_revision=gate.revision,
        prompt=gate.prompt,
        assistance_level="none",
        assistance_content=None,
        kind="standard",
        stage="independent_exit",
        issued_at=datetime.now(UTC),
    )
    _write_progress(client, "student-a", progress)
    headers = student_headers("student-a", course_ids=[COURSE_ID])
    assert client.get(URL, headers=headers).status_code == 409
    executor = AgentToolExecutor(
        canvas_workspace=client.app.state.canvas_workspace,
        course_id=COURSE_ID,
        lecture_id="lecture-open",
        user_id="student-a",
        user_message="Please annotate this.",
    )
    result = executor.execute(
        "write",
        {
            "path": "/lecture/annotations/note.json",
            "content": json.dumps({"block_id": "intro", "comment": "Note"}),
        },
    )
    assert not result["ok"] and "independent attempt" in result["error"]
