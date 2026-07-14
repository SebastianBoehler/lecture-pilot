from datetime import date
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

import lecturepilot.course_update_recovery as update_recovery
import lecturepilot.course_update_storage as update_storage
from auth_helpers import professor_headers
from lecturepilot.app import create_app
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.course_schedule_store import (
    overwrite_course_workspace,
    read_course_workspace,
    write_course_workspace,
)
from lecturepilot.course_update import (
    CourseUpdateError,
    begin_course_update_apply,
    finish_course_update_apply,
    mark_course_update_committed,
    require_update_accepting_uploads,
)
from lecturepilot.course_update_recovery import retire_committed_course_update
from lecturepilot.course_update_storage import (
    CourseUpdateRecoveryError,
    staged_file_transaction,
)
from lecturepilot.models import Course, CourseWorkspaceResult, Lecture
from lecturepilot.storage_layout import StorageLayout


def test_workspace_read_rolls_back_update_interrupted_before_commit(tmp_path: Path) -> None:
    layout, workspace = _course(tmp_path)
    course_root = layout.course_root(workspace.course.id)
    update_id = _update(layout, workspace.course.id)
    update_root = layout.course_update_root(workspace.course.id, update_id)
    staged = layout.course_update_uploads_dir(workspace.course.id, update_id)
    live = layout.course_uploads_dir(workspace.course.id)
    live.mkdir(parents=True)
    (staged / "Lecture01.tex").write_text("updated", encoding="utf-8")
    (live / "Lecture01.tex").write_text("original", encoding="utf-8")
    marker = begin_course_update_apply(layout, workspace.course.id, update_id)
    workspace_path = course_root / "builder" / "course-workspace.json"

    with staged_file_transaction(
        staged_root=staged,
        live_root=live,
        backup_root=update_root / "recovery",
        paths=["Lecture01.tex"],
        cleanup_on_success=False,
    ) as transaction:
        transaction.track_file(workspace_path, "builder/course-workspace.json")
        transaction.checkpoint()
        overwrite_course_workspace(
            course_root,
            workspace.model_copy(
                update={"course": workspace.course.model_copy(update={"title": "Interrupted"})}
            ),
        )

    assert (live / "Lecture01.tex").read_text(encoding="utf-8") == "updated"
    assert marker.exists()

    recovered = read_course_workspace(course_root, workspace.course.id)

    assert recovered is not None
    assert recovered.course.title == "Crash Recovery"
    assert (live / "Lecture01.tex").read_text(encoding="utf-8") == "original"
    assert not marker.exists()
    assert staged.is_dir()
    assert not (update_root / "recovery").exists()


def test_cleanup_crash_after_rollback_cannot_leave_active_broken_recovery(
    tmp_path: Path, monkeypatch
) -> None:
    layout, workspace = _course(tmp_path)
    course_root = layout.course_root(workspace.course.id)
    update_id = _update(layout, workspace.course.id)
    update_root = layout.course_update_root(workspace.course.id, update_id)
    staged = layout.course_update_uploads_dir(workspace.course.id, update_id)
    live = layout.course_uploads_dir(workspace.course.id)
    live.mkdir(parents=True)
    (staged / "Lecture01.tex").write_text("updated", encoding="utf-8")
    (live / "Lecture01.tex").write_text("original", encoding="utf-8")
    marker = begin_course_update_apply(layout, workspace.course.id, update_id)
    with staged_file_transaction(
        staged_root=staged,
        live_root=live,
        backup_root=update_root / "recovery",
        paths=["Lecture01.tex"],
        cleanup_on_success=False,
    ):
        pass

    class SimulatedProcessCrash(BaseException):
        pass

    def partially_remove_then_crash(path: Path) -> None:
        next(path.rglob("Lecture01.tex")).unlink()
        raise SimulatedProcessCrash

    with monkeypatch.context() as crash:
        crash.setattr(update_storage.shutil, "rmtree", partially_remove_then_crash)
        with pytest.raises(CourseUpdateRecoveryError):
            read_course_workspace(course_root, workspace.course.id)

    assert (live / "Lecture01.tex").read_text(encoding="utf-8") == "original"
    assert not marker.exists()
    recovered = read_course_workspace(course_root, workspace.course.id)
    assert recovered is not None
    assert recovered.course.title == "Crash Recovery"
    assert not (update_root / ".retired-recovery").exists()


def test_workspace_read_finishes_cleanup_for_committed_update(tmp_path: Path) -> None:
    layout, workspace = _course(tmp_path)
    update_id = _update(layout, workspace.course.id)
    update_root = layout.course_update_root(workspace.course.id, update_id)
    marker = begin_course_update_apply(layout, workspace.course.id, update_id)
    committed = workspace.model_copy(
        update={"course": workspace.course.model_copy(update={"title": "Committed"})}
    )
    overwrite_course_workspace(layout.course_root(workspace.course.id), committed)
    mark_course_update_committed(marker)

    recovered = read_course_workspace(layout.course_root(workspace.course.id), workspace.course.id)

    assert recovered is not None
    assert recovered.course.title == "Committed"
    assert not update_root.exists()


def test_committed_cleanup_crash_cannot_make_update_rollback_eligible(
    tmp_path: Path, monkeypatch
) -> None:
    layout, workspace = _course(tmp_path)
    update_id = _update(layout, workspace.course.id)
    update_root = layout.course_update_root(workspace.course.id, update_id)
    marker = begin_course_update_apply(layout, workspace.course.id, update_id)
    committed = workspace.model_copy(
        update={"course": workspace.course.model_copy(update={"title": "Committed"})}
    )
    overwrite_course_workspace(layout.course_root(workspace.course.id), committed)
    mark_course_update_committed(marker)

    class SimulatedProcessCrash(BaseException):
        pass

    def simulate_crash(_path: Path) -> None:
        raise SimulatedProcessCrash

    with monkeypatch.context() as crash:
        crash.setattr(update_recovery.shutil, "rmtree", simulate_crash)
        with pytest.raises(SimulatedProcessCrash):
            retire_committed_course_update(update_root)

    assert not update_root.exists()
    recovered = read_course_workspace(layout.course_root(workspace.course.id), workspace.course.id)
    assert recovered is not None
    assert recovered.course.title == "Committed"
    retired_root = layout.course_root(workspace.course.id) / "builder" / ".retired-updates"
    assert list(retired_root.iterdir()) == []


def test_retirement_error_preserves_committed_recovery_state(tmp_path: Path, monkeypatch) -> None:
    layout, workspace = _course(tmp_path)
    update_id = _update(layout, workspace.course.id)
    update_root = layout.course_update_root(workspace.course.id, update_id)
    marker = begin_course_update_apply(layout, workspace.course.id, update_id)
    mark_course_update_committed(marker)

    def fail_rename(_source: Path, _target: Path) -> None:
        raise OSError("simulated retirement failure")

    with monkeypatch.context() as failure:
        failure.setattr(update_recovery.os, "rename", fail_rename)
        with pytest.raises(OSError, match="simulated retirement failure"):
            try:
                retire_committed_course_update(update_root)
            except BaseException:
                finish_course_update_apply(marker)
                raise

    assert marker.is_file()
    assert (update_root / ".committed").is_file()
    with pytest.raises(CourseUpdateError, match="no longer accepts"):
        require_update_accepting_uploads(layout, workspace.course.id, update_id)

    assert read_course_workspace(layout.course_root(workspace.course.id), workspace.course.id)
    assert not update_root.exists()


def test_invalid_recovery_record_blocks_course_reads(tmp_path: Path) -> None:
    layout, workspace = _course(tmp_path)
    update_id = _update(layout, workspace.course.id)
    update_root = layout.course_update_root(workspace.course.id, update_id)
    begin_course_update_apply(layout, workspace.course.id, update_id)
    record = update_root / "recovery" / str(uuid4()) / "recovery.json"
    record.parent.mkdir(parents=True)
    record.write_text("{}", encoding="utf-8")

    with pytest.raises(CourseUpdateRecoveryError) as caught:
        read_course_workspace(layout.course_root(workspace.course.id), workspace.course.id)

    assert caught.value.recovery_id == record.parent.name
    assert update_root.exists()


def test_recovery_failure_returns_traceable_api_error(tmp_path: Path) -> None:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "materials",
    )
    layout, workspace = _course(tmp_path)
    update_id = _update(layout, workspace.course.id)
    update_root = layout.course_update_root(workspace.course.id, update_id)
    begin_course_update_apply(layout, workspace.course.id, update_id)
    record = update_root / "recovery" / str(uuid4()) / "recovery.json"
    record.parent.mkdir(parents=True)
    record.write_text("{}", encoding="utf-8")

    response = TestClient(app).get("/courses", headers=professor_headers())

    assert response.status_code == 500
    assert record.parent.name in response.json()["detail"]


def _course(tmp_path: Path) -> tuple[StorageLayout, CourseWorkspaceResult]:
    layout = StorageLayout(tmp_path / "workspaces")
    course = Course(
        id="crash-recovery",
        title="Crash Recovery",
        professor="Professor",
        term="Sommer 2026",
    )
    workspace = CourseWorkspaceResult(
        course=course,
        lectures=[
            Lecture(
                id="lecture-01",
                course_id=course.id,
                title="First",
                date=date(2026, 5, 6),
            )
        ],
        active_lecture_id="lecture-01",
    )
    write_course_workspace(layout.course_root(course.id), workspace)
    return layout, workspace


def _update(layout: StorageLayout, course_id: str) -> str:
    update_id = str(uuid4())
    layout.course_update_uploads_dir(course_id, update_id).mkdir(parents=True)
    return update_id
