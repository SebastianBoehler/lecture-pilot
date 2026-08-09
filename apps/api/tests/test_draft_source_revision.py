from datetime import date
from pathlib import Path

from lecturepilot.course_canvas_repairs import lecture_source_revision
from lecturepilot.course_schedule_store import overwrite_course_workspace
from lecturepilot.course_source_routing import source_revision
from lecturepilot.course_source_routing_models import (
    CourseSourceRoute,
    CourseSourceRoutingManifest,
    SourceRouteRole,
)
from lecturepilot.lecture_source_manifest import write_lecture_source_manifest
from lecturepilot.models import Course, CourseWorkspaceResult, Lecture
from lecturepilot.source_index_models import CourseSourceIndex, IndexedSourceFile
from lecturepilot.storage_layout import StorageLayout


def test_draft_source_revision_includes_current_schedule_and_semantic_routing(
    tmp_path: Path,
) -> None:
    layout = StorageLayout(tmp_path / "workspaces")
    course_id = "course-1"
    lecture = Lecture(
        id="lecture-01",
        course_id=course_id,
        title="Original title",
        date=date(2026, 5, 1),
        material_path="lecture.md",
    )
    index = CourseSourceIndex(
        course_id=course_id,
        files=[
            IndexedSourceFile(
                path="lecture.md",
                kind="markdown",
                size_bytes=10,
                sha256="a" * 64,
                modified_ns=1,
            )
        ],
    )
    index_path = layout.course_source_index_path(course_id)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(index.model_dump_json(indent=2), encoding="utf-8")
    write_lecture_source_manifest(
        layout.lecture_source_manifest_path(course_id, lecture.id),
        course_id=course_id,
        lecture_id=lecture.id,
        file_paths=["lecture.md"],
        source_index=index,
    )
    _write_workspace(layout, course_id, lecture)
    routing_path = layout.course_source_routing_path(course_id)
    routing = CourseSourceRoutingManifest(
        course_id=course_id,
        source_revision=source_revision(index, [lecture]),
        confirmed=True,
        routes=[
            CourseSourceRoute(
                path="lecture.md",
                kind="markdown",
                sha256="a" * 64,
                role=SourceRouteRole.LECTURE,
                lecture_id=lecture.id,
            )
        ],
    )
    routing_path.write_text(routing.model_dump_json(indent=2), encoding="utf-8")
    original = lecture_source_revision(layout, course_id=course_id, lecture_id=lecture.id)

    changed_lecture = lecture.model_copy(update={"title": "Changed title"})
    _write_workspace(layout, course_id, changed_lecture)
    changed_schedule = lecture_source_revision(layout, course_id=course_id, lecture_id=lecture.id)
    _write_workspace(layout, course_id, lecture)
    routing.routes[0] = routing.routes[0].model_copy(
        update={"role": SourceRouteRole.EXCLUDED, "lecture_id": None}
    )
    routing_path.write_text(routing.model_dump_json(indent=2), encoding="utf-8")
    changed_routing = lecture_source_revision(layout, course_id=course_id, lecture_id=lecture.id)

    assert original is not None
    assert changed_schedule != original
    assert changed_routing != original


def _write_workspace(layout: StorageLayout, course_id: str, lecture: Lecture) -> None:
    overwrite_course_workspace(
        layout.course_root(course_id),
        CourseWorkspaceResult(
            course=Course(
                id=course_id,
                title="Course",
                professor="Professor",
                term="Sommer 2026",
            ),
            lectures=[lecture],
            active_lecture_id=lecture.id,
        ),
    )
