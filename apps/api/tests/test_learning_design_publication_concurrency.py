from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event

from auth_helpers import professor_headers
from lecturepilot import course_canvas_store as course_canvas_store_module
from lecturepilot import course_learning_design_store as learning_design_store_module
from lecturepilot.course_learning_design_store import CourseLearningDesignStore
from lecturepilot.course_update_recovery import locked_course_state

from test_learning_design_review_routes import _client_with_draft, _review_path


def test_publish_holds_course_source_and_canvas_snapshot_until_commit(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client_with_draft(tmp_path)
    review = client.get(_review_path(), headers=professor_headers()).json()
    approved = client.post(
        f"{_review_path()}/approve",
        headers=professor_headers(),
        json={
            "draft_digest": review["draft_digest"],
            "source_revision": review["source_revision"],
        },
    )
    assert approved.status_code == 200
    workspace = client.app.state.canvas_workspace
    original = course_canvas_store_module._write_validated_publication
    publish_entered = Event()
    release_publish = Event()
    source_mutation_entered = Event()

    def paused_publish(**kwargs):
        publish_entered.set()
        assert release_publish.wait(timeout=2)
        return original(**kwargs)

    def mutate_source() -> None:
        with locked_course_state(workspace.course_media_root("design-course")):
            source_mutation_entered.set()

    monkeypatch.setattr(
        course_canvas_store_module,
        "_write_validated_publication",
        paused_publish,
    )
    with ThreadPoolExecutor(max_workers=2) as executor:
        publishing = executor.submit(
            workspace.publish_course_canvas_draft,
            course_id="design-course",
            lecture_id="lecture-01",
            published_by="prof01",
        )
        assert publish_entered.wait(timeout=2)
        mutation = executor.submit(mutate_source)
        assert not source_mutation_entered.wait(timeout=0.2)
        release_publish.set()
        assert publishing.result(timeout=2)["version"] == 1
        mutation.result(timeout=2)

    assert source_mutation_entered.is_set()


def test_approval_holds_course_source_state_until_artifact_commit(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client_with_draft(tmp_path)
    workspace = client.app.state.canvas_workspace
    reviews = CourseLearningDesignStore(workspace.layout)
    review = reviews.read(course_id="design-course", lecture_id="lecture-01")
    original = learning_design_store_module._write_review
    approval_entered = Event()
    release_approval = Event()
    source_mutation_entered = Event()

    def paused_write(path, changed):
        approval_entered.set()
        assert release_approval.wait(timeout=2)
        original(path, changed)

    def mutate_source() -> None:
        with locked_course_state(workspace.course_media_root("design-course")):
            source_mutation_entered.set()

    monkeypatch.setattr(learning_design_store_module, "_write_review", paused_write)
    with ThreadPoolExecutor(max_workers=2) as executor:
        approving = executor.submit(
            reviews.approve,
            course_id="design-course",
            lecture_id="lecture-01",
            draft_digest=review.draft_digest,
            source_revision=review.source_revision,
            approved_by="prof01",
        )
        assert approval_entered.wait(timeout=2)
        mutation = executor.submit(mutate_source)
        assert not source_mutation_entered.wait(timeout=0.2)
        release_approval.set()
        assert approving.result(timeout=2).approval is not None
        mutation.result(timeout=2)

    assert source_mutation_entered.is_set()
