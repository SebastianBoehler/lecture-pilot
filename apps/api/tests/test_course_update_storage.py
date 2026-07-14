from pathlib import Path
from threading import Event, Thread

from fastapi.testclient import TestClient
import pytest

import lecturepilot.course_update_storage as storage
import lecturepilot.course_update_routes as update_routes
from auth_helpers import professor_headers
from lecturepilot.app import create_app
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.course_update import begin_course_update_apply, discard_course_update
from lecturepilot.course_update_storage import (
    CourseUpdateRecoveryError,
    course_update_lock,
    staged_file_transaction,
)


def test_failed_rollback_keeps_recovery_artifact(tmp_path: Path, monkeypatch) -> None:
    staged = tmp_path / "staged"
    live = tmp_path / "live"
    recoveries = tmp_path / "recoveries"
    staged.mkdir()
    live.mkdir()
    (staged / "Lecture01.tex").write_text("updated", encoding="utf-8")
    (live / "Lecture01.tex").write_text("original", encoding="utf-8")
    original_copy = storage._atomic_copy

    def fail_backup_restore(source: Path, target: Path) -> None:
        if recoveries in source.parents and live in target.parents:
            raise OSError("simulated rollback failure")
        original_copy(source, target)

    monkeypatch.setattr(storage, "_atomic_copy", fail_backup_restore)

    with pytest.raises(CourseUpdateRecoveryError) as caught:
        with staged_file_transaction(
            staged_root=staged,
            live_root=live,
            backup_root=recoveries,
            paths=["Lecture01.tex"],
        ):
            raise RuntimeError("simulated metadata failure")

    artifact = recoveries / caught.value.recovery_id
    assert artifact.is_dir()
    assert (artifact / "source" / "Lecture01.tex").read_text(encoding="utf-8") == "original"
    assert (artifact / "recovery.json").is_file()
    assert "Lecture01.tex" in (artifact / "recovery.json").read_text(encoding="utf-8")


def test_tracked_metadata_is_restored_with_source_files(tmp_path: Path) -> None:
    staged = tmp_path / "staged"
    live = tmp_path / "live"
    recoveries = tmp_path / "recoveries"
    metadata = tmp_path / "course" / "builder" / "course-workspace.json"
    staged.mkdir()
    live.mkdir()
    metadata.parent.mkdir(parents=True)
    (staged / "Lecture01.tex").write_text("updated", encoding="utf-8")
    (live / "Lecture01.tex").write_text("original", encoding="utf-8")
    metadata.write_text("original metadata", encoding="utf-8")

    with pytest.raises(RuntimeError, match="stop transaction"):
        with staged_file_transaction(
            staged_root=staged,
            live_root=live,
            backup_root=recoveries,
            paths=["Lecture01.tex"],
        ) as transaction:
            transaction.track_file(metadata, "builder/course-workspace.json")
            metadata.write_text("changed metadata", encoding="utf-8")
            raise RuntimeError("stop transaction")

    assert (live / "Lecture01.tex").read_text(encoding="utf-8") == "original"
    assert metadata.read_text(encoding="utf-8") == "original metadata"
    assert not recoveries.exists()


def test_recovery_cleanup_rename_failure_keeps_recovery_active(tmp_path: Path, monkeypatch) -> None:
    staged = tmp_path / "staged"
    live = tmp_path / "live"
    recoveries = tmp_path / "recoveries"
    staged.mkdir()
    live.mkdir()
    (staged / "Lecture01.tex").write_text("updated", encoding="utf-8")
    (live / "Lecture01.tex").write_text("original", encoding="utf-8")

    def fail_retirement(_source: Path, _target: Path) -> None:
        raise OSError("simulated recovery retirement failure")

    monkeypatch.setattr(storage.os, "rename", fail_retirement)
    with pytest.raises(CourseUpdateRecoveryError) as caught:
        with staged_file_transaction(
            staged_root=staged,
            live_root=live,
            backup_root=recoveries,
            paths=["Lecture01.tex"],
        ):
            raise RuntimeError("trigger rollback")

    assert (live / "Lecture01.tex").read_text(encoding="utf-8") == "original"
    assert (recoveries / caught.value.recovery_id / "recovery.json").is_file()


def test_course_update_lock_serializes_threads(tmp_path: Path) -> None:
    course_root = tmp_path / "course"
    first_entered = Event()
    release_first = Event()
    second_entered = Event()

    def first() -> None:
        with course_update_lock(course_root):
            first_entered.set()
            assert release_first.wait(timeout=2)

    def second() -> None:
        assert first_entered.wait(timeout=2)
        with course_update_lock(course_root):
            second_entered.set()

    first_thread = Thread(target=first)
    second_thread = Thread(target=second)
    first_thread.start()
    second_thread.start()
    assert first_entered.wait(timeout=2)
    assert not second_entered.wait(timeout=0.05)
    release_first.set()
    first_thread.join(timeout=2)
    second_thread.join(timeout=2)

    assert not first_thread.is_alive()
    assert not second_thread.is_alive()
    assert second_entered.is_set()


def test_staged_upload_is_discarded_if_update_closes_before_promotion(
    tmp_path: Path, monkeypatch
) -> None:
    client = _course_client(tmp_path)
    update_id = _create_update(client)
    layout = client.app.state.canvas_workspace.layout
    original_stage = update_routes.stage_course_upload

    async def stage_then_discard_update(*args, **kwargs):
        staged = await original_stage(*args, **kwargs)
        discard_course_update(layout, "update-demo", update_id)
        return staged

    monkeypatch.setattr(update_routes, "stage_course_upload", stage_then_discard_update)
    response = client.post(
        f"/admin/courses/update-demo/updates/{update_id}/materials",
        headers=professor_headers(),
        data={"path": "Lecture01.tex"},
        files={"file": ("Lecture01.tex", b"\\documentclass{beamer}", "text/plain")},
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]
    assert not (
        layout.course_update_uploads_dir("update-demo", update_id) / "Lecture01.tex"
    ).exists()
    quarantine = layout.course_root("update-demo").parent / ".upload-quarantine" / "update-demo"
    assert list(quarantine.glob("*.part")) == []


def test_discard_recovers_update_that_never_started_mutating(tmp_path: Path) -> None:
    client = _course_client(tmp_path)
    update_id = _create_update(client)
    layout = client.app.state.canvas_workspace.layout
    begin_course_update_apply(layout, "update-demo", update_id)

    response = client.delete(
        f"/admin/courses/update-demo/updates/{update_id}", headers=professor_headers()
    )

    assert response.status_code == 204
    assert not layout.course_update_root("update-demo", update_id).exists()


def _course_client(tmp_path: Path) -> TestClient:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "materials",
    )
    client = TestClient(app)
    response = client.post(
        "/admin/course-workspaces",
        headers=professor_headers(),
        json={
            "course_title": "Update Demo",
            "target": "full-course",
            "lectures": [{"number": "01", "title": "First", "date": "2026-05-06"}],
        },
    )
    assert response.status_code == 200
    return client


def _create_update(client: TestClient) -> str:
    response = client.post("/admin/courses/update-demo/updates", headers=professor_headers())
    assert response.status_code == 200
    return response.json()["update_id"]
