from pathlib import Path

from auth_helpers import student_headers
from test_quiz_attempt_review_fixes import COURSE_ID, LECTURE_ID, _client, _publish


def test_rendered_canvas_version_remains_submission_authority_after_republish(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    headers = student_headers("student-a", course_ids=[COURSE_ID])
    canvas = client.get(
        f"/courses/{COURSE_ID}/lectures/{LECTURE_ID}/canvas",
        headers=headers,
    )
    first_context = client.app.state.canvas_workspace.course_canvas_store.read_analytics_context(
        course_id=COURSE_ID,
        lecture_id=LECTURE_ID,
    )

    assert canvas.status_code == 200
    view = canvas.json()
    assert view["publication_version"] == 1
    assert view["learning_map_revision"] == first_context.learning_map_revision
    assert view["document"]["sections"][0]["blocks"][0]["text"] == ("What should be minimized?")
    assert "answer_index" not in view["document"]["sections"][0]["blocks"][0]

    _publish(client, version_two=True)
    current_state = client.get(
        f"/courses/{COURSE_ID}/lectures/{LECTURE_ID}/learner-state",
        headers=headers,
    )
    stale = client.post(
        f"/courses/{COURSE_ID}/lectures/{LECTURE_ID}/analytics/quiz-answer",
        headers=headers,
        json={
            "attendance": "present",
            "attempt_id": "rendered-version-one-attempt",
            "block_id": "risk-quiz",
            "option_index": 1,
            "publication_version": view["publication_version"],
        },
    )

    assert current_state.status_code == 200
    assert current_state.json()["publication_version"] == 2
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "stale_quiz_publication"
    refreshed_state = client.get(
        f"/courses/{COURSE_ID}/lectures/{LECTURE_ID}/learner-state",
        headers=headers,
    ).json()
    assert refreshed_state["quiz_states"] == {}
    assert (
        client.app.state.analytics_store.events(
            course_id=COURSE_ID,
            lecture_id=LECTURE_ID,
        )
        == []
    )
