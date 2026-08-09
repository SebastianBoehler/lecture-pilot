import json
from pathlib import Path

from fastapi.testclient import TestClient

from auth_helpers import student_headers
from test_learner_lesson_state_routes import COURSE_ID, QUIZ_ANSWER, STATE_URL, _client


def test_malformed_persisted_quiz_state_fails_read_and_write_without_replacement(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    user_id = "student-corrupt"
    path = (
        client.app.state.canvas_workspace.layout.user_lecture_root(
            user_id, COURSE_ID, "lecture-open"
        )
        / "quizzes.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "course_id": COURSE_ID,
                "lecture_id": "lecture-open",
                "updated_at": "2026-08-09T10:00:00+00:00",
                "quizzes": {
                    "intro-quiz": {
                        "selected_index": 0,
                        "correct": True,
                        "attempt_index": 1,
                        "first_attempt_correct": True,
                        "latest_outcome": "correct",
                        "correction_state": "not_needed",
                    }
                },
                "attempts": {},
            }
        ),
        encoding="utf-8",
    )
    original = path.read_bytes()
    headers = student_headers(user_id, course_ids=[COURSE_ID])

    state = client.get(STATE_URL, headers=headers)
    submit = client.post(
        f"/courses/{COURSE_ID}/lectures/lecture-open/analytics/quiz-answer",
        headers=headers,
        json={**QUIZ_ANSWER, "attempt_id": "must-not-overwrite"},
    )

    assert state.status_code == submit.status_code == 409
    assert state.json()["detail"] == submit.json()["detail"]
    assert state.json()["detail"] == "Persisted learner quiz state is invalid."
    assert path.read_bytes() == original


def test_quiz_store_rejects_extra_root_fields(tmp_path: Path) -> None:
    client = _client(tmp_path)
    user_id = "student-extra"
    path = (
        client.app.state.canvas_workspace.layout.user_lecture_root(
            user_id, COURSE_ID, "lecture-open"
        )
        / "quizzes.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "course_id": COURSE_ID,
                "lecture_id": "lecture-open",
                "updated_at": "2026-08-09T10:00:00+00:00",
                "quizzes": {},
                "attempts": {},
                "unexpected_version": 1,
            }
        ),
        encoding="utf-8",
    )

    response = client.get(
        STATE_URL,
        headers=student_headers(user_id, course_ids=[COURSE_ID]),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Persisted learner quiz state is invalid."


def test_non_utf8_quiz_state_rejects_read_and_submit_without_writes(tmp_path: Path) -> None:
    configured_client = _client(tmp_path)
    client = TestClient(configured_client.app, raise_server_exceptions=False)
    user_id = "student-non-utf8"
    path = (
        client.app.state.canvas_workspace.layout.user_lecture_root(
            user_id, COURSE_ID, "lecture-open"
        )
        / "quizzes.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\xff\xfe\x80not-utf8")
    original = path.read_bytes()
    headers = student_headers(user_id, course_ids=[COURSE_ID])

    state = client.get(STATE_URL, headers=headers)
    submit = client.post(
        f"/courses/{COURSE_ID}/lectures/lecture-open/analytics/quiz-answer",
        headers=headers,
        json={**QUIZ_ANSWER, "attempt_id": "must-not-write"},
    )

    expected = {"detail": "Persisted learner quiz state is invalid."}
    assert state.status_code == submit.status_code == 409
    assert state.json() == submit.json() == expected
    for response in (state, submit):
        assert "codec" not in response.text.lower()
        assert str(path) not in response.text
        assert "not-utf8" not in response.text
    assert path.read_bytes() == original
    assert (
        client.app.state.analytics_store.events(
            course_id=COURSE_ID,
            lecture_id="lecture-open",
        )
        == []
    )
