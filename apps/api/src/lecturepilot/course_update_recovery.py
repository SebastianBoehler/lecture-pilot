from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
import json
import logging
import os
from pathlib import Path, PurePosixPath
import shutil
from uuid import uuid4

from lecturepilot.course_update_storage import (
    CourseUpdateRecoveryError,
    cleanup_retired_recovery_artifact,
    course_update_lock,
    course_update_lock_held,
    retire_recovery_artifact,
)
from lecturepilot.durable_files import atomic_copy, ensure_durable_directory, fsync_directory
from lecturepilot.workspace_capability import CapabilityRoot, WorkspaceCapability
from lecturepilot.workspace_fs import WorkspaceFS


logger = logging.getLogger(__name__)


@contextmanager
def locked_course_state(course_root: Path) -> Iterator[None]:
    """Recover interrupted work, then hold the shared course mutation lock."""

    with course_update_lock(course_root):
        _recover_locked(course_root)
        yield


def recover_interrupted_course_updates(course_root: Path) -> None:
    if course_update_lock_held(course_root):
        return
    with course_update_lock(course_root):
        _recover_locked(course_root)


def _recover_locked(course_root: Path) -> None:
    _cleanup_retired_updates(course_root)
    updates_root = course_root / "builder" / "updates"
    if not updates_root.is_dir():
        return
    for update_root in sorted(path for path in updates_root.iterdir() if path.is_dir()):
        _cleanup_retired_recoveries(update_root)
        if not os.path.lexists(update_root / ".applying"):
            continue
        try:
            _recover_update(course_root, update_root)
        except BaseException as exc:
            recovery_id = _recovery_id(update_root)
            logger.exception(
                "Course update crash recovery failed; update_id=%s recovery_id=%s",
                update_root.name,
                recovery_id,
            )
            raise CourseUpdateRecoveryError(recovery_id) from exc


def _recover_update(course_root: Path, update_root: Path) -> None:
    if (update_root / ".committed").is_file():
        retire_committed_course_update(update_root)
        return
    recovery_root = update_root / "recovery"
    markers = sorted(recovery_root.glob("*/recovery.json")) if recovery_root.is_dir() else []
    if len(markers) > 1:
        raise ValueError("Course update has multiple recovery records.")
    if markers:
        _restore_record(course_root, markers[0].parent, markers[0])
        logger.warning(
            "Recovered interrupted course update; update_id=%s recovery_id=%s",
            update_root.name,
            markers[0].parent.name,
        )
    retired = retire_recovery_artifact(
        recovery_root,
        retired_root=update_root / ".retired-recovery",
    )
    (update_root / ".applying").unlink(missing_ok=True)
    fsync_directory(update_root)
    cleanup_retired_recovery_artifact(retired)


def _restore_record(course_root: Path, recovery_dir: Path, marker: Path) -> None:
    payload = json.loads(marker.read_text(encoding="utf-8"))
    operations = payload.get("operations") if isinstance(payload, dict) else None
    if not isinstance(operations, list):
        raise ValueError("Course update recovery record is invalid.")
    backup = _workspace("/recovery", recovery_dir, writable=False)
    live = _workspace("/course", course_root, writable=True)
    for operation in reversed(operations):
        if not isinstance(operation, dict):
            raise ValueError("Course update recovery operation is invalid.")
        logical = _validated_logical_path(operation.get("path"))
        target = _recovery_target(live, logical)
        action = operation.get("action")
        if action == "restore":
            saved = backup.resolve(f"/recovery/{logical.as_posix()}").path
            atomic_copy(saved, target)
        elif action == "delete":
            if target.exists():
                target.unlink()
                fsync_directory(target.parent)
        else:
            raise ValueError("Course update recovery action is invalid.")


def _validated_logical_path(value: object) -> PurePosixPath:
    if not isinstance(value, str):
        raise ValueError("Course update recovery path is invalid.")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or len(path.parts) < 2:
        raise ValueError("Course update recovery path is invalid.")
    if path.parts[0] not in {"source", "metadata"}:
        raise ValueError("Course update recovery path is invalid.")
    return path


def _recovery_target(live: WorkspaceFS, logical: PurePosixPath) -> Path:
    relative = PurePosixPath(*logical.parts[1:]).as_posix()
    target = f"source/uploads/{relative}" if logical.parts[0] == "source" else relative
    return live.resolve(f"/course/{target}", for_write=True).path


def retire_committed_course_update(update_root: Path) -> None:
    """Move committed state out of the recovery namespace before deleting it."""

    if not (update_root / ".committed").is_file():
        raise ValueError("Only committed course updates can be retired.")
    updates_root = update_root.parent
    retired_root = updates_root.parent / ".retired-updates"
    ensure_durable_directory(retired_root)
    retired = retired_root / f"{update_root.name}-{uuid4()}"
    os.rename(update_root, retired)
    fsync_directory(updates_root)
    fsync_directory(retired_root)
    _remove_retired_update(retired)


def _cleanup_retired_updates(course_root: Path) -> None:
    retired_root = course_root / "builder" / ".retired-updates"
    if not retired_root.is_dir():
        return
    for retired in sorted(path for path in retired_root.iterdir() if path.is_dir()):
        _remove_retired_update(retired)


def _remove_retired_update(retired: Path) -> None:
    try:
        shutil.rmtree(retired)
        fsync_directory(retired.parent)
    except Exception:
        logger.warning("Could not remove retired course update; path=%s", retired, exc_info=True)


def _cleanup_retired_recoveries(update_root: Path) -> None:
    retired_root = update_root / ".retired-recovery"
    if not retired_root.is_dir():
        return
    for retired in sorted(path for path in retired_root.iterdir() if path.is_dir()):
        cleanup_retired_recovery_artifact(retired)


def _recovery_id(update_root: Path) -> str:
    recovery_root = update_root / "recovery"
    records = sorted(recovery_root.glob("*/recovery.json")) if recovery_root.is_dir() else []
    return records[0].parent.name if len(records) == 1 else update_root.name


def _workspace(logical: str, root: Path, *, writable: bool) -> WorkspaceFS:
    return WorkspaceFS(WorkspaceCapability((CapabilityRoot(logical, root, writable=writable),)))
