from datetime import date
from hashlib import sha256

from canvas_workspace_fixtures import approve_canvas_draft, published_course_canvas
from practice_design_test_helpers import approved_design_document
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.course_canvas_repairs import lecture_source_revision
from lecturepilot.course_schedule_store import write_course_workspace
from lecturepilot.course_source_routing import source_revision
from lecturepilot.course_source_routing_models import CourseSourceRoute, CourseSourceRoutingManifest
from lecturepilot.lecture_source_manifest import LectureSourceFile, LectureSourceManifest
from lecturepilot.models import Course, CourseWorkspaceResult, Lecture
from lecturepilot.source_index_models import CourseSourceIndex, IndexedSourceFile


def published_source_workspace(tmp_path):
    workspace = CanvasWorkspace(workspace_root=tmp_path, material_root=tmp_path / "material")
    layout = workspace.layout
    uploads = layout.course_uploads_dir("course-a")
    uploads.mkdir(parents=True)
    names = ("current.md", "future.md", "unassigned.md", "course-wide.md")
    for name in names:
        (uploads / name).write_text(f"secret {name}")
    index = CourseSourceIndex(
        course_id="course-a",
        files=[
            IndexedSourceFile(
                path=name,
                kind="markdown",
                size_bytes=(uploads / name).stat().st_size,
                sha256=sha256((uploads / name).read_bytes()).hexdigest(),
                modified_ns=1,
            )
            for name in names
        ],
    )
    lectures = [
        Lecture(id=identifier, course_id="course-a", title=identifier, date=date(2020, 1, 1))
        for identifier in ("lecture-open", "lecture-future")
    ]
    write_course_workspace(
        layout.course_root("course-a"),
        CourseWorkspaceResult(
            course=Course(id="course-a", title="Course", professor="Professor", term="Term"),
            lectures=lectures,
            active_lecture_id="lecture-open",
        ),
    )
    index_path = layout.course_source_index_path("course-a")
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(index.model_dump_json())
    roles = (
        ("lecture", "lecture-open"),
        ("lecture", "lecture-future"),
        ("excluded", None),
        ("course_wide", None),
    )
    routing = CourseSourceRoutingManifest(
        course_id="course-a",
        confirmed=True,
        source_revision=source_revision(index, lectures),
        routes=[
            CourseSourceRoute(
                path=item.path, kind=item.kind, sha256=item.sha256, role=role, lecture_id=lecture_id
            )
            for item, (role, lecture_id) in zip(index.files, roles, strict=True)
        ],
    )
    routing_path = layout.course_source_routing_path("course-a")
    routing_path.parent.mkdir(parents=True, exist_ok=True)
    routing_path.write_text(routing.model_dump_json())
    manifest = LectureSourceManifest(
        course_id="course-a",
        lecture_id="lecture-open",
        files=[LectureSourceFile(path=index.files[0].path, sha256=index.files[0].sha256)],
    )
    manifest_path = layout.lecture_source_manifest_path("course-a", "lecture-open")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(manifest.model_dump_json())
    revision = lecture_source_revision(layout, course_id="course-a", lecture_id="lecture-open")
    document = published_course_canvas("course-a", "lecture-open")
    document = document.model_copy(
        update={
            "source_ref": "current.md",
            "sections": [
                section.model_copy(update={"source_ref": "current.md"})
                for section in document.sections
            ],
        }
    )
    document, design = approved_design_document(
        layout, document, source_revision=revision, source_path="current.md"
    )
    workspace.write_course_canvas_draft(
        document, expected_source_revision=revision, practice_design=design
    )
    approve_canvas_draft(workspace, "course-a", "lecture-open")
    workspace.publish_course_canvas_draft(
        course_id="course-a", lecture_id="lecture-open", published_by="professor"
    )
    return workspace
