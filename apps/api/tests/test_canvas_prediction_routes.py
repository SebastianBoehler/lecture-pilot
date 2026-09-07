from datetime import UTC, datetime

from auth_helpers import student_headers
from canvas_workspace_fixtures import publish_course_canvas
from lecturepilot.canvas_models import CanvasBlock
from lecturepilot.canvas_predictions import prediction_context
from lecturepilot.coaching_state_models import CoachingProgress, PendingCheck
from lecturepilot.models import AgentTurnInput
from test_learner_lesson_state_routes import _client, _gate, _write_progress, COURSE_ID

URL = f"/courses/{COURSE_ID}/lectures/lecture-open/predictions"


def test_prediction_http_lifecycle_and_tutor_context(tmp_path):
    client = _client(tmp_path)
    workspace = client.app.state.canvas_workspace
    snapshot = workspace.course_canvas_store.read_current_published_snapshot(
        course_id=COURSE_ID,
        lecture_id="lecture-open",
    )
    doc = snapshot.document
    for section in doc.sections:
        section.blocks = [b for b in section.blocks if not b.id.startswith("practice-")]
    doc.sections[0].blocks.insert(
        0, CanvasBlock(id="prediction", type="prediction", text="What happens next?")
    )
    publication = publish_course_canvas(workspace, doc)
    version = publication.version
    owner = student_headers("student-a", course_ids=[COURSE_ID])
    body = {"block_id": "prediction", "publication_version": version, "answer": "My guess"}
    assert client.get(URL).status_code == 401
    assert client.get(URL, headers=student_headers("outsider", course_ids=[])).status_code == 404
    assert (
        client.post(
            URL, headers=owner, json={**body, "publication_version": version + 1}
        ).status_code
        == 409
    )
    assert (
        client.post(
            URL, headers=owner, json={"block_id": "prediction", "publication_version": version}
        ).status_code
        == 422
    )
    result = client.post(URL, headers=owner, json=body)
    assert result.status_code == 200, result.text
    assert client.get(URL, headers=owner).json()[0]["answer"] == "My guess"
    assert (
        client.get(URL, headers=student_headers("student-b", course_ids=[COURSE_ID])).json() == []
    )
    assert client.post(URL, headers=owner, json={**body, "answer": "New guess"}).status_code == 409
    turn = AgentTurnInput(
        user_id="student-a",
        course_id=COURSE_ID,
        lecture_id="lecture-open",
        attendance="present",
        message="Can we revisit my prediction?",
    )
    assert prediction_context(workspace, turn)[0].answer == "My guess"
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
    assert client.get(URL, headers=owner).status_code == 409
    assert client.post(URL, headers=owner, json=body).status_code == 409
    assert prediction_context(workspace, turn) == []
