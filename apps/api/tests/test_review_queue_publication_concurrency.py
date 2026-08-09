from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from threading import Barrier

from auth_helpers import student_headers
from canvas_workspace_fixtures import approve_canvas_draft, write_canvas_draft
from lecturepilot.canvas_models import CanvasBlock
from review_queue_test_helpers import (
    COURSE_ID,
    NOW,
    gate_revision,
    read_progress,
    review_client,
    write_review,
)
from canvas_workspace_fixtures import published_course_canvas


def test_review_open_racing_real_republish_binds_one_atomic_gate_revision(
    tmp_path: Path,
) -> None:
    client = review_client(tmp_path)
    user_id = "student-a"
    headers = student_headers(user_id, course_ids=[COURSE_ID])
    write_review(client, user_id, "lecture-a", "gate-a", NOW - timedelta(days=1))
    old_revision = gate_revision(client, "lecture-a", "gate-a")
    workspace = client.app.state.canvas_workspace
    replacement = published_course_canvas(COURSE_ID, "lecture-a")
    replacement.sections[0] = replacement.sections[0].model_copy(
        update={
            "id": "section-a",
            "title": "Section A republished",
            "blocks": [
                CanvasBlock(
                    id="gate-a",
                    type="checkpoint",
                    text="Explain A under the republished contract.",
                )
            ],
        }
    )
    write_canvas_draft(workspace, replacement)
    approve_canvas_draft(workspace, COURSE_ID, "lecture-a")
    start = Barrier(3)
    open_url = f"/courses/{COURSE_ID}/review-queue/gates/lecture-a/gate-a/open"

    def open_review():
        start.wait()
        return client.post(open_url, headers=headers)

    def publish():
        start.wait()
        return workspace.publish_course_canvas_draft(
            course_id=COURSE_ID,
            lecture_id="lecture-a",
            published_by="professor-a",
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        opening = executor.submit(open_review)
        publishing = executor.submit(publish)
        start.wait()
        response = opening.result(timeout=5)
        publishing.result(timeout=5)

    new_revision = gate_revision(client, "lecture-a", "gate-a")
    assert new_revision != old_revision
    assert response.status_code in {200, 409}
    pending = read_progress(client, user_id, "lecture-a").pending_check
    if response.status_code == 200:
        assert response.json()["gate_revision"] == old_revision
        assert pending is not None
        assert pending.gate_revision == old_revision
    else:
        assert pending is None
    queue = client.get(f"/courses/{COURSE_ID}/review-queue", headers=headers)
    assert queue.status_code == 409
