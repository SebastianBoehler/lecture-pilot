from __future__ import annotations

from pathlib import Path
import shutil
from uuid import UUID, uuid4

from lecturepilot.course_schedule_store import read_course_workspace
from lecturepilot.storage_layout import StorageLayout


class CourseUpdateError(ValueError):
    """Raised when a staged course update is missing or internally inconsistent."""


def create_course_update(layout: StorageLayout, course_id: str) -> str:
    require_workspace(layout, course_id)
    update_id = str(uuid4())
    layout.course_update_uploads_dir(course_id, update_id).mkdir(
        parents=True, mode=0o700, exist_ok=False
    )
    return update_id


def update_uploads_dir(layout: StorageLayout, course_id: str, update_id: str) -> Path:
    root = require_update_root(layout, course_id, update_id)
    uploads = root / "uploads"
    uploads.mkdir(parents=True, mode=0o700, exist_ok=True)
    return uploads


def discard_course_update(layout: StorageLayout, course_id: str, update_id: str) -> None:
    shutil.rmtree(require_update_root(layout, course_id, update_id))


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
