from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

from canvas_workspace_fixtures import publish_course_canvas, published_course_canvas
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.course_canvas_repairs import lecture_source_revision
from lecturepilot.course_learning_design_store import (
    CourseLearningDesignStore,
    LearningDesignApprovalRequiredError,
    LearningDesignStaleError,
)


def test_republish_racing_real_regeneration_never_publishes_unapproved_draft(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    replacement = published_course_canvas("design-course", "lecture-01").model_copy(
        update={"title": "Regenerated draft"}
    )
    revision = _revision(workspace)
    start = Barrier(3)

    def publish():
        start.wait()
        try:
            return workspace.publish_course_canvas_draft(
                course_id="design-course",
                lecture_id="lecture-01",
                published_by="professor",
            )
        except LearningDesignApprovalRequiredError:
            return None

    def regenerate():
        start.wait()
        return workspace.write_course_canvas_draft(
            replacement,
            expected_source_revision=revision,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        publishing = executor.submit(publish)
        regenerating = executor.submit(regenerate)
        start.wait()
        publication = publishing.result(timeout=5)
        regenerating.result(timeout=5)

    snapshot = workspace.course_canvas_store.read_current_published_snapshot(
        course_id="design-course",
        lecture_id="lecture-01",
    )
    assert snapshot is not None
    assert snapshot.document.title == "Published lecture"
    assert snapshot.version == (2 if publication is not None else 1)
    review = CourseLearningDesignStore(workspace.layout).read(
        course_id="design-course",
        lecture_id="lecture-01",
    )
    assert review.approval is None


def test_approval_racing_real_regeneration_cannot_approve_different_draft(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    reviews = CourseLearningDesignStore(workspace.layout)
    current = reviews.read(course_id="design-course", lecture_id="lecture-01")
    replacement = published_course_canvas("design-course", "lecture-01").model_copy(
        update={"title": "Different draft"}
    )
    start = Barrier(3)

    def approve():
        start.wait()
        try:
            return reviews.approve(
                course_id="design-course",
                lecture_id="lecture-01",
                draft_digest=current.draft_digest,
                source_revision=current.source_revision,
                learning_map_revision=current.learning_map.revision,
                report_revision=current.report.report_revision,
                approved_by="professor",
            )
        except LearningDesignStaleError:
            return None

    def regenerate():
        start.wait()
        return workspace.write_course_canvas_draft(
            replacement,
            expected_source_revision=_revision(workspace),
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        approving = executor.submit(approve)
        regenerating = executor.submit(regenerate)
        start.wait()
        approving.result(timeout=5)
        regenerating.result(timeout=5)

    changed = reviews.read(course_id="design-course", lecture_id="lecture-01")
    assert changed.draft_digest != current.draft_digest
    assert changed.approval is None


def _workspace(tmp_path: Path) -> CanvasWorkspace:
    workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "materials",
    )
    publish_course_canvas(
        workspace,
        published_course_canvas("design-course", "lecture-01"),
    )
    return workspace


def _revision(workspace: CanvasWorkspace) -> str:
    revision = lecture_source_revision(
        workspace.layout,
        course_id="design-course",
        lecture_id="lecture-01",
    )
    assert revision is not None
    return revision
