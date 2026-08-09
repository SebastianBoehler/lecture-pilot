import json
from pathlib import Path

from auth_helpers import student_headers
from test_learner_lesson_state_routes import COURSE_ID, QUIZ_ANSWER, _client, _state_url


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

    state = client.get(_state_url(), headers=headers)
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
        _state_url(),
        headers=student_headers(user_id, course_ids=[COURSE_ID]),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Persisted learner quiz state is invalid."
