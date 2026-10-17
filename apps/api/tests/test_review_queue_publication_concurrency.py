from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from threading import Barrier

from auth_helpers import student_headers
from canvas_workspace_fixtures import approve_canvas_draft
from approved_practice_design_helpers import revised_design, store_design
from lecturepilot.learning_design.course_practice_design_store import PracticeDesignStore
from review_queue_test_helpers import (
    COURSE_ID,
    NOW,
    gate_revision,
    read_progress,
    review_client,
    write_review,
)


def test_review_open_racing_real_republish_binds_one_atomic_gate_revision(
    tmp_path: Path,
) -> None:
    client = review_client(tmp_path)
    user_id = "student-a"
    headers = student_headers(user_id, course_ids=[COURSE_ID])
    write_review(client, user_id, "lecture-a", "practice-gate-a", NOW - timedelta(days=1))
    old_revision = gate_revision(client, "lecture-a", "practice-gate-a")
    workspace = client.app.state.canvas_workspace
    replacement = workspace.read_course_canvas_draft(
        course_id=COURSE_ID, lecture_id="lecture-a"
    ).model_copy(deep=True)
    replacement.sections[0].title = "Section A republished"
    new_prompt = "Explain A under the republished contract."
    for block in replacement.sections[0].blocks:
        if block.id == "practice-gate-a":
            block.text = new_prompt
    design = PracticeDesignStore(workspace.layout).read(course_id=COURSE_ID, lecture_id="lecture-a")
    design = store_design(
        workspace.layout,
        revised_design(
            design,
            targets=[
                item.model_copy(update={"baseline_task": new_prompt})
                if item.id == "gate-a"
                else item
                for item in design.targets
            ],
        ),
    )
    workspace.write_course_canvas_draft(
        replacement, expected_source_revision=design.source_revision, practice_design=design
    )
    approve_canvas_draft(workspace, COURSE_ID, "lecture-a")
    start = Barrier(3)
    open_url = f"/courses/{COURSE_ID}/review-queue/gates/lecture-a/practice-gate-a/open"

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

    new_revision = gate_revision(client, "lecture-a", "practice-gate-a")
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
