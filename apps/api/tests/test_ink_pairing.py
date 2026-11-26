from fastapi.testclient import TestClient

from auth_helpers import student_headers
from test_agent_stream import _published_app, _turn_payload
from test_tutor_camera import FRAME

LECTURE = "/courses/martius-ml/lectures/lecture-01"


def test_iPad_pair_is_account_scoped_and_can_transfer_one_page(tmp_path):
    client = TestClient(_published_app(tmp_path))
    owner = student_headers("u1")
    other = student_headers("u2")
    created = client.post(f"{LECTURE}/ink-pair", headers=owner)
    assert created.status_code == 200
    path = f"{LECTURE}/ink-pair/{created.json()['code']}"

    assert client.get(path, headers=owner).json() == {"image": None}
    assert client.put(path, headers=other, json={"image": FRAME}).status_code == 404
    assert client.put(path, headers=owner, json={"image": FRAME}).json() == {"received": True}
    assert client.get(path, headers=other).status_code == 404
    assert client.get(path, headers=owner).json() == {"image": FRAME}
    assert client.delete(path, headers=owner).status_code == 204
    assert client.get(path, headers=owner).status_code == 404


def test_recall_rejects_mismatched_published_section_before_inference(tmp_path):
    app = _published_app(tmp_path)
    snapshot = app.state.canvas_workspace.read_published_canvas_view(
        user_id="u1", course_id="martius-ml", lecture_id="lecture-01"
    )
    payload = {
        **_turn_payload(),
        "recall_publication_version": snapshot.version,
        "camera_frame": FRAME,
        "canvas_state": {"focused_section_id": "unknown"},
    }
    response = TestClient(app).post("/agent/turn", headers=student_headers("u1"), json=payload)
    assert response.status_code == 409
    assert "recall section is no longer published" in response.text


def test_save_correction_is_revision_bound_and_private(tmp_path):
    app = _published_app(tmp_path)
    snapshot = app.state.canvas_workspace.read_published_canvas_view(
        user_id="u1", course_id="martius-ml", lecture_id="lecture-01"
    )
    block_id = snapshot.document.sections[0].blocks[0].id
    client = TestClient(app)
    path = f"{LECTURE}/annotations"
    target = f"{path}/cf65fbf5-775a-41b6-82af-aa796110ca84"
    owner = student_headers("u1")
    payload = {
        "block_id": block_id,
        "publication_version": snapshot.version,
        "comment": "Remember the condition on the input.",
    }

    assert (
        client.put(target, headers=owner, json={**payload, "publication_version": 0}).status_code
        == 409
    )
    for _ in range(2):
        response = client.put(target, headers=owner, json=payload)
        assert response.status_code == 200
    notes = client.get(path, headers=owner).json()
    assert len(notes) == 1
    assert notes[0]["comment"] == payload["comment"]
    assert client.get(path, headers=student_headers("u2")).json() == []
