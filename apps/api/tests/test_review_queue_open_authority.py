from datetime import timedelta
from pathlib import Path

from auth_helpers import student_headers
from lecturepilot.coaching_state_models import review_key
from review_queue_test_helpers import (
    COURSE_ID,
    NOW,
    gate_revision as _gate_revision,
    read_progress as _read_progress,
    review_client as _client,
    write_progress as _write_progress,
    write_review as _write_review,
)


def test_open_rejects_locked_stale_and_wrong_gate_targets(tmp_path: Path) -> None:
    client = _client(tmp_path)
    user_id = "student-a"
    headers = student_headers(user_id, course_ids=[COURSE_ID])
    _write_review(client, user_id, "lecture-a", "gate-a", NOW - timedelta(days=1))
    _write_review(client, user_id, "lecture-locked", "gate-locked", NOW - timedelta(days=1))
    progress = _read_progress(client, user_id, "lecture-a")
    current_revision = _gate_revision(client, "lecture-a", "gate-a")
    key = review_key("gate-a", current_revision)
    progress.delayed_reviews[key] = progress.delayed_reviews[key].model_copy(
        update={"gate_revision": "stale-revision"}
    )
    _write_progress(client, user_id, "lecture-a", progress)

    stale = client.post(
        f"/courses/{COURSE_ID}/review-queue/gates/lecture-a/gate-a/open",
        headers=headers,
    )
    wrong = client.post(
        f"/courses/{COURSE_ID}/review-queue/gates/lecture-a/gate-b/open",
        headers=headers,
    )
    locked = client.post(
        f"/courses/{COURSE_ID}/review-queue/gates/lecture-locked/gate-locked/open",
        headers=headers,
    )
    unpublished_response = client.post(
        f"/courses/{COURSE_ID}/review-queue/gates/lecture-unpublished/gate-unpublished/open",
        headers=headers,
    )

    assert stale.status_code == 409
    assert wrong.status_code == 404
    assert locked.status_code == 403
    assert unpublished_response.status_code == 404
