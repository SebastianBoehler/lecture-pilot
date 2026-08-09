from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

from canvas_workspace_fixtures import publish_course_canvas, published_course_canvas
from lecturepilot.canvas_workspace import CanvasWorkspace


def test_concurrent_real_publishes_are_serialized_and_increment_versions(
    tmp_path: Path,
) -> None:
    workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "materials",
    )
    document = published_course_canvas("demo-course", "lecture-01")
    assert publish_course_canvas(workspace, document).version == 1
    start = Barrier(3)

    def publish(publisher: str):
        start.wait()
        return workspace.publish_course_canvas_draft(
            course_id="demo-course",
            lecture_id="lecture-01",
            published_by=publisher,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(publish, "professor-a")
        second = executor.submit(publish, "professor-b")
        start.wait()
        versions = sorted([first.result(timeout=5).version, second.result(timeout=5).version])

    assert versions == [2, 3]
    snapshot = workspace.course_canvas_store.read_current_published_snapshot(
        course_id="demo-course",
        lecture_id="lecture-01",
    )
    assert snapshot is not None
    assert snapshot.version == 3
    assert snapshot.publication.published_by in {"professor-a", "professor-b"}
