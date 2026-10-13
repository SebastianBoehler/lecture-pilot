from datetime import UTC, date, datetime
import json
from pathlib import Path

from lecturepilot.app import create_app
from lecturepilot.canvas.canvas_workspace import CanvasWorkspace
from lecturepilot.core.models import Course, CourseWorkspaceResult, Lecture
from lecturepilot.courses.course_schedule_store import overwrite_course_workspace
from lecturepilot.courses.lecture_states import course_lecture_states
from lecturepilot.sources.course_source_routing import source_revision
from lecturepilot.sources.course_source_routing_models import (
    CourseSourceRoute,
    CourseSourceRoutingManifest,
    SourceRouteRole,
)
from lecturepilot.sources.source_index_models import CourseSourceIndex, IndexedSourceFile
from test_practice_design_canvas_binding import COURSE_ID, _approved_design, _document
from test_practice_design_publication import _published_workspace

LECTURES = [
    Lecture(id="lecture-01", course_id=COURSE_ID, title="Evidence", date=date(2026, 5, 6)),
    Lecture(id="lecture-02", course_id=COURSE_ID, title="Bayes", date=date(2026, 5, 13)),
]


def test_published_lecture_is_done_and_an_unplanned_lecture_needs_goals(tmp_path) -> None:
    _write_sources(tmp_path)
    workspace, _design = _published_workspace(tmp_path)

    states = _states(workspace)

    assert states["routing"] == "confirmed"
    first, second = states["lectures"]
    assert first["published"] is True and first["published_at"] is not None
    assert _summary(first) == ("current", "approved", "published", "none")
    assert (first["number"], first["title"], first["date"]) == ("01", "Evidence", "2026-05-06")
    assert second["published"] is False and second["published_at"] is None
    assert _summary(second) == ("new", "missing", "none", "review_goals")


def test_changed_sources_stale_only_their_lecture(tmp_path) -> None:
    _write_sources(tmp_path)
    workspace, _design = _published_workspace(tmp_path)
    _write_sources(tmp_path, lecture_two="c")  # Another lecture's file changes: still current.
    assert _summary(_states(workspace)["lectures"][0]) == (
        "current",
        "approved",
        "published",
        "none",
    )

    _write_sources(tmp_path, lecture_one="b", lecture_two="c")

    first = _states(workspace)["lectures"][0]
    assert first["published"] is True
    assert _summary(first) == ("changed", "stale", "none", "keep_or_regenerate_goals")


def test_draft_progress_drives_the_next_action(tmp_path) -> None:
    _write_sources(tmp_path)
    workspace = _workspace(tmp_path)
    design = _approved_design(workspace)
    assert _summary(_states(workspace)["lectures"][0]) == (
        "current",
        "approved",
        "none",
        "generate_draft",
    )

    job = _write_job(workspace, status="running")
    assert _summary(_states(workspace)["lectures"][0])[2:] == ("generating", "wait")
    _write_job(workspace, status="failed", path=job, detail="Section 2 failed validation.")
    failed = _states(workspace)["lectures"][0]
    assert (failed["draft"], failed["draft_error"], failed["next_action"]) == (
        "failed",
        "Section 2 failed validation.",
        "retry_draft",
    )

    _write_job(workspace, status="completed", path=job)
    workspace.write_course_canvas_draft(
        _document(design), expected_source_revision=design.source_revision, practice_design=design
    )
    assert _summary(_states(workspace)["lectures"][0])[2:] == ("ready", "review_draft")


def test_unconfirmed_routing_comes_first(tmp_path) -> None:
    _write_sources(tmp_path, confirmed=False)
    states = _states(_workspace(tmp_path))
    assert states["routing"] == "needs_review"
    assert [item["next_action"] for item in states["lectures"]] == ["confirm_routing"] * 2


def _summary(state: dict) -> tuple:
    return state["sources"], state["goals"], state["draft"], state["next_action"]


def _workspace(tmp_path: Path) -> CanvasWorkspace:
    return CanvasWorkspace(
        workspace_root=tmp_path / "workspaces", material_root=tmp_path / "materials"
    )


def _states(workspace: CanvasWorkspace) -> dict:
    app = create_app()
    app.state.canvas_workspace = workspace
    return course_lecture_states(app, COURSE_ID).model_dump(mode="json")


def _write_sources(tmp_path, *, lecture_one="a", lecture_two="a", confirmed=True) -> None:
    layout = _workspace(tmp_path).layout
    files = {"lecture.md": lecture_one, "lecture2.md": lecture_two}
    index = CourseSourceIndex(
        course_id=COURSE_ID,
        files=[
            IndexedSourceFile(
                path=path, kind="markdown", size_bytes=1, sha256=digit * 64, modified_ns=1
            )
            for path, digit in files.items()
        ],
    )
    path = layout.course_source_index_path(COURSE_ID)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(index.model_dump_json(), encoding="utf-8")
    overwrite_course_workspace(
        layout.course_root(COURSE_ID),
        CourseWorkspaceResult(
            course=Course(id=COURSE_ID, title="Practice", professor="Prof", term="Sommer 2026"),
            lectures=LECTURES,
            active_lecture_id="lecture-01",
        ),
    )
    routing = CourseSourceRoutingManifest(
        course_id=COURSE_ID,
        source_revision=source_revision(index, LECTURES),
        confirmed=confirmed,
        routes=[
            CourseSourceRoute(
                path=path,
                kind="markdown",
                sha256=files[path] * 64,
                role=SourceRouteRole.LECTURE,
                lecture_id=lecture_id,
            )
            for path, lecture_id in (("lecture.md", "lecture-01"), ("lecture2.md", "lecture-02"))
        ],
    )
    layout.course_source_routing_path(COURSE_ID).write_text(routing.model_dump_json())


def _write_job(workspace, *, status, path=None, detail=None) -> Path:
    directory = workspace.layout.course_root(COURSE_ID) / "builder" / "generations" / "lecture-01"
    directory.mkdir(parents=True, exist_ok=True)
    path = path or directory / f"{'d' * 64}.json"
    now = datetime.now(UTC).isoformat()
    record = {
        "generation_id": "e" * 32,
        "course_id": COURSE_ID,
        "lecture_id": "lecture-01",
        "actor_key": "f" * 24,
        "request_key_hash": "d" * 64,
        "status": status,
        "attempt": 1,
        "created_at": now,
        "updated_at": now,
        "error_code": "canvas_generation_failed" if status == "failed" else None,
        "error_detail": detail,
    }
    path.write_text(json.dumps(record), encoding="utf-8")
    return path


def test_lecture_states_require_a_course_manager(tmp_path) -> None:
    from fastapi.testclient import TestClient

    from auth_helpers import student_headers

    app = create_app()
    app.state.canvas_workspace = _workspace(tmp_path)
    response = TestClient(app).get(
        f"/admin/courses/{COURSE_ID}/lecture-states", headers=student_headers()
    )
    assert response.status_code == 403


def test_draft_errors_hide_internal_file_paths() -> None:
    from lecturepilot.courses.lecture_states import readable_draft_error

    detail = (
        "/draft/lecture02-eng-why-iterate.md: Checkpoint block lecture02-why-iterate-check "
        "must contain a direct question or concrete task."
    )
    assert readable_draft_error(detail) == (
        "Checkpoint block lecture02-why-iterate-check must contain a direct question or "
        "concrete task."
    )
    assert readable_draft_error("Provider timed out.") == "Provider timed out."
    assert readable_draft_error(None) is None
