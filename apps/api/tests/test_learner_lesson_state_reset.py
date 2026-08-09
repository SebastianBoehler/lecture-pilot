from pathlib import Path

from auth_helpers import student_headers
from test_learner_lesson_state_routes import COURSE_ID, QUIZ_ANSWER, STATE_URL, _client


def test_progress_reset_clears_private_quiz_state(tmp_path: Path) -> None:
    client = _client(tmp_path)
    headers = student_headers("student-a", course_ids=[COURSE_ID])
    quiz_url = f"/courses/{COURSE_ID}/lectures/lecture-open/analytics/quiz-answer"
    assert client.post(quiz_url, headers=headers, json=QUIZ_ANSWER).status_code == 200

    reset = client.post(
        f"/courses/{COURSE_ID}/learner-workspace/reset",
        headers=headers,
        json={"reset_canvas": False, "reset_course_memory": False, "reset_progress": True},
    )

    assert reset.status_code == 200
    assert client.get(STATE_URL, headers=headers).json()["quiz_states"] == {}
