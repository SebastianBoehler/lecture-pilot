from __future__ import annotations

import os
from pathlib import Path
import shutil
from uuid import UUID, uuid4

from lecturepilot.course_schedule_store import read_course_workspace
from lecturepilot.course_update_recovery import locked_course_state
from lecturepilot.durable_files import (
    atomic_write_json,
    ensure_durable_directory,
    fsync_directory,
)
from lecturepilot.storage_layout import StorageLayout


class CourseUpdateError(ValueError):
    """Raised when a staged course update is missing or internally inconsistent."""


_APPLY_MARKER = ".applying"
_COMMITTED_MARKER = ".committed"


def create_course_update(layout: StorageLayout, course_id: str) -> str:
    with locked_course_state(layout.course_root(course_id)):
        require_workspace(layout, course_id)
        update_id = str(uuid4())
        uploads = layout.course_update_uploads_dir(course_id, update_id)
        if uploads.exists():
            raise FileExistsError(uploads)
        ensure_durable_directory(uploads)
    return update_id


def update_uploads_dir(layout: StorageLayout, course_id: str, update_id: str) -> Path:
    root = require_update_accepting_uploads(layout, course_id, update_id)
    uploads = root / "uploads"
    ensure_durable_directory(uploads)
    return uploads


def discard_course_update(layout: StorageLayout, course_id: str, update_id: str) -> None:
    with locked_course_state(layout.course_root(course_id)):
        root = require_update_accepting_uploads(layout, course_id, update_id)
        shutil.rmtree(root)


def begin_course_update_apply(layout: StorageLayout, course_id: str, update_id: str) -> Path:
    root = require_update_root(layout, course_id, update_id)
    marker = root / _APPLY_MARKER
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(marker, flags, 0o600)
    except FileExistsError as exc:
        raise CourseUpdateError(
            "Course update is already being applied or requires recovery."
        ) from exc
    try:
        os.write(descriptor, b"applying\n")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    fsync_directory(marker.parent)
    return marker


def finish_course_update_apply(marker: Path) -> None:
    if not marker.parent.exists() or (marker.parent / _COMMITTED_MARKER).is_file():
        return
    recovery = marker.parent / "recovery"
    if recovery.is_dir() and any(recovery.glob("*/recovery.json")):
        return
    marker.unlink(missing_ok=True)
    fsync_directory(marker.parent)


def mark_course_update_committed(marker: Path) -> None:
    atomic_write_json(marker.parent / _COMMITTED_MARKER, {"status": "committed"})


def require_update_accepting_uploads(layout: StorageLayout, course_id: str, update_id: str) -> Path:
    root = require_update_root(layout, course_id, update_id)
    if os.path.lexists(root / _APPLY_MARKER):
        raise CourseUpdateError("Course update no longer accepts material uploads.")
    return root


def require_workspace(layout: StorageLayout, course_id: str):
    workspace = read_course_workspace(layout.course_root(course_id), course_id)
    if workspace is None:
        raise CourseUpdateError("Course workspace not found.")
    return workspace


def require_update_root(layout: StorageLayout, course_id: str, update_id: str) -> Path:
    try:
        UUID(update_id)
    except ValueError as exc:
        raise CourseUpdateError("Course update not found.") from exc
    root = layout.course_update_root(course_id, update_id)
    if not root.is_dir():
        raise CourseUpdateError("Course update not found.")
    return root
