from datetime import timedelta
from pathlib import Path

from auth_helpers import student_headers
from lecturepilot.coaching_progress import CoachingProgressStore
from review_queue_test_helpers import (
    COURSE_ID,
    NOW,
    read_progress,
    review_client,
    write_review,
)


def test_reopening_same_delayed_check_keeps_original_binding(tmp_path: Path) -> None:
    client = review_client(tmp_path)
    user_id = "student-a"
    write_review(client, user_id, "lecture-a", "gate-a", NOW - timedelta(days=1))
    url = f"/courses/{COURSE_ID}/review-queue/gates/lecture-a/gate-a/open"
    headers = student_headers(user_id, course_ids=[COURSE_ID])

    first = client.post(url, headers=headers)
    original = read_progress(client, user_id, "lecture-a").pending_check
    second = client.post(url, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert original is not None
    assert read_progress(client, user_id, "lecture-a").pending_check == original


def test_open_delayed_check_preserves_another_pending_assessment(tmp_path: Path) -> None:
    client = review_client(tmp_path)
    user_id = "student-a"
    write_review(client, user_id, "lecture-a", "gate-a", NOW - timedelta(days=1))
    learning_map = client.app.state.canvas_workspace.course_canvas_store.learning_map(
        course_id=COURSE_ID,
        lecture_id="lecture-a",
    )
    assert learning_map is not None
    other_gate = next(gate for gate in learning_map.gates if gate.id == "gate-c")
    store = CoachingProgressStore(client.app.state.canvas_workspace.layout)
    store.bind_inline_checkpoint(
        user_id=user_id,
        course_id=COURSE_ID,
        lecture_id="lecture-a",
        gate=other_gate,
        now=NOW,
    )
    original = read_progress(client, user_id, "lecture-a").pending_check

    response = client.post(
        f"/courses/{COURSE_ID}/review-queue/gates/lecture-a/gate-a/open",
        headers=student_headers(user_id, course_ids=[COURSE_ID]),
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Another assessment is already pending."}
    assert read_progress(client, user_id, "lecture-a").pending_check == original
