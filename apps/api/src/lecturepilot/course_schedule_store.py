from __future__ import annotations

import os
from pathlib import Path
import tempfile

from lecturepilot.course_update_recovery import recover_interrupted_course_updates
from lecturepilot.durable_files import ensure_durable_directory, fsync_directory
from lecturepilot.course_workspace import merge_course_workspace
from lecturepilot.models import CourseWorkspaceResult


def write_course_workspace(
    course_root: Path,
    workspace: CourseWorkspaceResult,
    *,
    replace_lectures: bool = False,
) -> CourseWorkspaceResult:
    target = _workspace_path(course_root)
    ensure_durable_directory(target.parent)
    if target.exists():
        existing = read_course_workspace(course_root, workspace.course.id)
        workspace = merge_course_workspace(
            existing,
            workspace,
            replace_lectures=replace_lectures,
        )
    _atomic_write(target, workspace.model_dump_json(indent=2))
    return workspace


def overwrite_course_workspace(
    course_root: Path,
    workspace: CourseWorkspaceResult,
) -> CourseWorkspaceResult:
    target = _workspace_path(course_root)
    ensure_durable_directory(target.parent)
    _atomic_write(target, workspace.model_dump_json(indent=2))
    return workspace


def read_course_workspace(course_root: Path, course_id: str) -> CourseWorkspaceResult | None:
    recover_interrupted_course_updates(course_root)
    source = _workspace_path(course_root)
    if not source.exists():
        return None
    workspace = CourseWorkspaceResult.model_validate_json(source.read_text(encoding="utf-8"))
    if workspace.course.id != course_id:
        return None
    return workspace


def list_course_workspaces(workspace_root: Path, tenant_id: str) -> list[CourseWorkspaceResult]:
    root = workspace_root / "courses" / tenant_id
    if not root.exists():
        return []
    workspaces: list[CourseWorkspaceResult] = []
    for source in sorted(root.glob("*/builder/course-workspace.json")):
        try:
            recover_interrupted_course_updates(source.parent.parent)
            workspaces.append(
                CourseWorkspaceResult.model_validate_json(source.read_text(encoding="utf-8"))
            )
        except ValueError:
            continue
    return workspaces


def _workspace_path(course_root: Path) -> Path:
    return course_root / "builder" / "course-workspace.json"


def _atomic_write(path: Path, content: str) -> None:
    descriptor, temporary = tempfile.mkstemp(prefix=".course-workspace-", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        temporary_path.replace(path)
        fsync_directory(path.parent)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise
