from __future__ import annotations

from pathlib import Path

from lecturepilot.course_workspace import merge_course_workspace
from lecturepilot.models import CourseWorkspaceResult


def write_course_workspace(course_root: Path, workspace: CourseWorkspaceResult) -> CourseWorkspaceResult:
    target = _workspace_path(course_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        existing = read_course_workspace(course_root, workspace.course.id)
        workspace = merge_course_workspace(existing, workspace)
    target.write_text(workspace.model_dump_json(indent=2), encoding="utf-8")
    return workspace


def read_course_workspace(course_root: Path, course_id: str) -> CourseWorkspaceResult | None:
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
            workspaces.append(CourseWorkspaceResult.model_validate_json(source.read_text(encoding="utf-8")))
        except ValueError:
            continue
    return workspaces


def _workspace_path(course_root: Path) -> Path:
    return course_root / "builder" / "course-workspace.json"
