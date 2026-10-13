from datetime import date
from pathlib import Path

from lecturepilot.core.models import Course, CourseWorkspaceResult, Lecture
from lecturepilot.core.storage_layout import StorageLayout
from lecturepilot.courses.course_schedule_store import overwrite_course_workspace
from lecturepilot.migrations_storage import storage_migration_lecture_source_alias as migration
from lecturepilot.sources.course_source_routing import source_revision
from lecturepilot.sources.course_source_routing_models import (
    CourseSourceRoute,
    CourseSourceRoutingManifest,
    SourceRouteRole,
)
from lecturepilot.sources.lecture_source_manifest import write_lecture_source_manifest
from lecturepilot.sources.lecture_source_revision import lecture_source_revision
from lecturepilot.sources.source_index_models import CourseSourceIndex, IndexedSourceFile

COURSE_ID = "course-1"
LECTURES = {"lecture-01": "Lecture01.tex", "lecture-02": "Lecture02.tex"}


class Course_:
    def __init__(self, tmp_path: Path) -> None:
        self.layout = StorageLayout(tmp_path / "workspaces")
        self.lectures = {
            lecture_id: Lecture(
                id=lecture_id,
                course_id=COURSE_ID,
                title=f"Title {lecture_id}",
                date=date(2026, 5, index),
                material_path=path,
            )
            for index, (lecture_id, path) in enumerate(LECTURES.items(), start=1)
        }
        self.files = {path: "1" for path in LECTURES.values()} | {"macros.sty": "1"}
        self.routes = {path: (SourceRouteRole.LECTURE, lid) for lid, path in LECTURES.items()}
        self.routes["macros.sty"] = (SourceRouteRole.COURSE_WIDE, None)
        self.write()

    def write(self, *, manifests: bool = True) -> None:
        index = CourseSourceIndex(
            course_id=COURSE_ID,
            files=[
                IndexedSourceFile(
                    path=path, kind="latex", size_bytes=1, sha256=digit * 64, modified_ns=1
                )
                for path, digit in sorted(self.files.items())
            ],
        )
        index_path = self.layout.course_source_index_path(COURSE_ID)
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text(index.model_dump_json(), encoding="utf-8")
        overwrite_course_workspace(
            self.layout.course_root(COURSE_ID),
            CourseWorkspaceResult(
                course=Course(id=COURSE_ID, title="Course", professor="Prof", term="Sommer 2026"),
                lectures=list(self.lectures.values()),
                active_lecture_id="lecture-01",
            ),
        )
        routing = CourseSourceRoutingManifest(
            course_id=COURSE_ID,
            source_revision=source_revision(index, list(self.lectures.values())),
            confirmed=True,
            routes=[
                CourseSourceRoute(
                    path=path,
                    kind="latex",
                    sha256=self.files[path] * 64,
                    role=role,
                    lecture_id=lecture_id,
                )
                for path, (role, lecture_id) in sorted(self.routes.items())
            ],
        )
        self.layout.course_source_routing_path(COURSE_ID).write_text(
            routing.model_dump_json(), encoding="utf-8"
        )
        if not manifests:
            return
        for lecture_id in self.lectures:
            write_lecture_source_manifest(
                self.layout.lecture_source_manifest_path(COURSE_ID, lecture_id),
                course_id=COURSE_ID,
                lecture_id=lecture_id,
                file_paths=[
                    path
                    for path, (role, owner) in self.routes.items()
                    if role == SourceRouteRole.COURSE_WIDE or owner == lecture_id
                ],
                source_index=index,
            )

    def revision(self, lecture_id: str = "lecture-01") -> str | None:
        return lecture_source_revision(self.layout, course_id=COURSE_ID, lecture_id=lecture_id)

    def add_lecture(self, lecture_id: str, path: str) -> None:
        self.lectures[lecture_id] = Lecture(
            id=lecture_id, course_id=COURSE_ID, title="New", date=date(2026, 5, 20)
        )
        self.files[path] = "1"
        self.routes[path] = (SourceRouteRole.LECTURE, lecture_id)


def test_other_lectures_and_unrelated_uploads_leave_a_lecture_revision_unchanged(tmp_path):
    course = Course_(tmp_path)
    before = course.revision()
    assert before is not None

    course.add_lecture("lecture-03", "Lecture03.tex")
    course.files["Lecture02.tex"] = "2"
    course.lectures["lecture-02"] = course.lectures["lecture-02"].model_copy(
        update={"title": "Renamed"}
    )
    course.files["notes/unused.md"] = "3"
    course.routes["notes/unused.md"] = (SourceRouteRole.EXCLUDED, None)
    course.write()

    assert course.revision() == before
    assert course.revision("lecture-02") != before


def test_own_files_course_wide_files_routes_and_schedule_change_the_revision(tmp_path):
    course = Course_(tmp_path)
    before = course.revision()

    course.files["Lecture01.tex"] = "2"
    course.write(manifests=False)  # Content changes count before manifests are refreshed.
    own_file = course.revision()
    course.files["Lecture01.tex"] = "1"
    course.files["macros.sty"] = "2"
    course.write()
    shared = course.revision()
    course.files["macros.sty"] = "1"
    course.routes["Lecture02.tex"] = (SourceRouteRole.LECTURE, "lecture-01")
    course.write()
    rerouted = course.revision()
    course.routes["Lecture02.tex"] = (SourceRouteRole.LECTURE, "lecture-02")
    course.lectures["lecture-01"] = course.lectures["lecture-01"].model_copy(
        update={"date": date(2026, 6, 1)}
    )
    course.write()
    rescheduled = course.revision()

    assert len({before, own_file, shared, rerouted, rescheduled}) == 5


def test_migration_keeps_legacy_bindings_current_until_the_lecture_changes(tmp_path):
    course = Course_(tmp_path)
    legacy = migration.legacy_lecture_source_revision(
        course.layout, course_id=COURSE_ID, lecture_id="lecture-01"
    )
    assert legacy is not None and course.revision() != legacy

    # Only lecture-01 has stored work bound to its legacy revision.
    design = course.layout.lecture_practice_design_path(COURSE_ID, "lecture-01")
    design.parent.mkdir(parents=True, exist_ok=True)
    design.write_text(f'{{"source_revision": "{legacy}"}}', encoding="utf-8")

    dry_run = migration.migrate(course.layout.root)
    assert dry_run["aliased"] == [
        "courses/tenant-tuebingen/course-1/builder/source-manifests/lecture-01.json"
    ]
    assert dry_run["unbound"] == 1
    assert not course.layout.lecture_source_alias_path(COURSE_ID, "lecture-01").exists()
    migration.migrate(course.layout.root, apply=True)
    assert not course.layout.lecture_source_alias_path(COURSE_ID, "lecture-02").exists()

    # Approvals bound to the legacy revision stay current, also after unrelated changes.
    assert course.revision() == legacy
    course.add_lecture("lecture-03", "Lecture03.tex")
    course.write()
    assert course.revision() == legacy
    rerun = migration.migrate(course.layout.root, apply=True)
    assert rerun["existing"] == 1 and course.revision() == legacy

    course.files["Lecture01.tex"] = "2"
    course.write()
    assert course.revision() not in {None, legacy}
    course.files["Lecture01.tex"] = "1"
    course.write()
    assert course.revision() == legacy  # Identical inputs are the same sources again.


def test_courses_without_routing_use_the_lecture_manifest(tmp_path):
    course = Course_(tmp_path)
    routing = course.layout.course_source_routing_path(COURSE_ID)
    routing.unlink()
    before = course.revision()
    assert before is not None

    course.files["Lecture02.tex"] = "2"
    course.write(manifests=False)
    routing.unlink()
    assert course.revision() == before
    course.files["Lecture01.tex"] = "2"
    course.write(manifests=False)
    routing.unlink()
    assert course.revision() != before
