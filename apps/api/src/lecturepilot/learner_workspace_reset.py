from __future__ import annotations

import shutil
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from lecturepilot.storage_layout import StorageLayout, safe_id
from lecturepilot.professor_preview import is_professor_preview_user_id


class LearnerWorkspaceResetInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reset_canvas: bool = True
    reset_course_memory: bool = True
    reset_progress: bool = False


class LearnerWorkspaceResetResult(BaseModel):
    course_id: str
    user_id: str
    reset_canvas: bool
    reset_course_memory: bool
    reset_progress: bool
    deleted_paths: int


def reset_learner_workspace(
    *,
    layout: StorageLayout,
    course_id: str,
    user_id: str,
    request: LearnerWorkspaceResetInput,
) -> LearnerWorkspaceResetResult:
    deleted_paths = 0
    for course_root in _course_roots(layout, user_id, course_id):
        deleted_paths += _reset_course_root(course_root, request)
    if request.reset_course_memory:
        deleted_paths += _delete_path(layout.user_course_memories_dir(user_id, course_id))
        if is_professor_preview_user_id(user_id):
            deleted_paths += _delete_path(layout.user_memories_dir(user_id))
    return LearnerWorkspaceResetResult(
        course_id=course_id,
        user_id=user_id,
        reset_canvas=request.reset_canvas,
        reset_course_memory=request.reset_course_memory,
        reset_progress=request.reset_progress,
        deleted_paths=deleted_paths,
    )


def _course_roots(layout: StorageLayout, user_id: str, course_id: str) -> list[Path]:
    user_key = layout.user_key(user_id)
    return [
        layout.user_course_root(user_id, course_id),
        layout.root / "workspaces" / "students" / user_key / "courses" / safe_id(course_id),
    ]


def _reset_course_root(course_root: Path, request: LearnerWorkspaceResetInput) -> int:
    deleted_paths = 0
    if request.reset_progress:
        deleted_paths += _delete_path(course_root / "progress.json")
    lectures_root = course_root / "lectures"
    if not lectures_root.exists():
        return deleted_paths
    for lecture_root in sorted(path for path in lectures_root.iterdir() if path.is_dir()):
        if request.reset_canvas:
            deleted_paths += _delete_path(lecture_root / "canvas")
            deleted_paths += _delete_path(lecture_root / "canvas.json")
        if request.reset_progress:
            deleted_paths += _delete_path(lecture_root / "attendance.json")
            deleted_paths += _delete_path(lecture_root / "gates.json")
            deleted_paths += _delete_path(lecture_root / "tutor-state.json")
    return deleted_paths


def _delete_path(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
    return 1
