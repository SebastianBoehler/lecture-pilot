from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from threading import Event

from auth_helpers import student_headers
from canvas_workspace_fixtures import published_course_canvas
from lecturepilot import review_queue_routes as review_queue_routes_module
from lecturepilot.canvas_models import CanvasBlock
from review_queue_test_helpers import (
    COURSE_ID,
    NOW,
    gate_revision,
    read_progress,
    review_client,
    write_review,
)


def test_republish_waits_until_due_review_open_commits_authoritative_map(
    tmp_path: Path,
    monkeypatch,
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
    workspace.write_course_canvas_draft(replacement)
    bind_entered = Event()
    release_bind = Event()
    publication_finished = Event()
    original_bind = review_queue_routes_module.bind_delayed_review

    def controlled_bind(*args, **kwargs):
        bind_entered.set()
        assert release_bind.wait(timeout=3)
        return original_bind(*args, **kwargs)

    monkeypatch.setattr(review_queue_routes_module, "bind_delayed_review", controlled_bind)
    open_url = f"/courses/{COURSE_ID}/review-queue/gates/lecture-a/gate-a/open"

    def publish() -> dict:
        result = workspace.publish_course_canvas_draft(
            course_id=COURSE_ID,
            lecture_id="lecture-a",
            published_by="professor-a",
        )
        publication_finished.set()
        return result

    with ThreadPoolExecutor(max_workers=2) as executor:
        opening = executor.submit(client.post, open_url, headers=headers)
        assert bind_entered.wait(timeout=3)
        publication = executor.submit(publish)
        publish_waited = not publication_finished.wait(timeout=0.2)
        release_bind.set()
        response = opening.result(timeout=3)
        publication.result(timeout=3)

    assert publish_waited
    assert response.status_code == 200
    assert response.json()["gate_revision"] == old_revision
    assert response.json()["prompt"] == "Apply A to an unfamiliar case."
    pending = read_progress(client, user_id, "lecture-a").pending_check
    assert pending is not None
    assert pending.gate_revision == old_revision
    assert pending.prompt == "Apply A to an unfamiliar case."
    assert gate_revision(client, "lecture-a", "gate-a") != old_revision
    assert client.get(f"/courses/{COURSE_ID}/review-queue", headers=headers).json()["items"] == []
    assert client.post(open_url, headers=headers).status_code == 409
