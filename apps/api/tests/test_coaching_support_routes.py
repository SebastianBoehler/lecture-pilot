from auth_helpers import student_headers
from lecturepilot.coaching_progress import CoachingProgressStore
from test_learner_lesson_state_routes import _client, _gate, COURSE_ID, STATE_URL


def test_support_endpoint_auth_binding_exposure_and_reload(tmp_path):
    client = _client(tmp_path)
    gate = _gate(client, "practice-practice-target")
    store = CoachingProgressStore(client.app.state.canvas_workspace.layout)
    ids = dict(user_id="student-a", course_id=COURSE_ID, lecture_id="lecture-open")
    store.bind_inline_checkpoint(**ids, gate=gate)
    headers = student_headers("student-a", course_ids=[COURSE_ID])
    pending = client.get(STATE_URL, headers=headers).json()["pending_check"]
    payload = {key: pending[key] for key in ("gate_id", "gate_revision", "task_id", "issued_at")}
    url = STATE_URL + "/support"
    assert client.post(url, json=payload).status_code == 401
    assert (
        client.post(
            url,
            json=payload,
            headers=student_headers(
                "student-b",
                course_ids=[COURSE_ID],
            ),
        ).status_code
        == 409
    )
    assert (
        client.post(
            url,
            json=payload,
            headers=student_headers(
                "student-a",
                course_ids=["another-course"],
            ),
        ).status_code
        == 404
    )
    result = client.post(url, json=payload, headers=headers)
    assert result.status_code == 200, result.text
    pending = result.json()["pending_check"]
    assert pending["stage"] == "diagnostic_support"
    assert pending["assistance_content"] == gate.hint_ladder[0].content
    assert not pending["focus_required"]
    assert client.get(STATE_URL, headers=headers).json()["pending_check"] == pending
    assert client.post(url, json=payload, headers=headers).status_code == 409
    assert not store.read(**ids).turns
    exposure = store.read(**ids).task_exposures[f"{gate.id}@{gate.revision}@baseline"]
    assert exposure.supported and not exposure.answered
