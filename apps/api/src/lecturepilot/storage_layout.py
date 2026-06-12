from __future__ import annotations

import re
from hashlib import sha256
from pathlib import Path


DEFAULT_TENANT_ID = "tenant-tuebingen"


class StorageLayoutError(ValueError):
    """Raised when a logical storage id cannot be mapped to a safe path."""


class StorageLayout:
    """Path builder for the agent-visible LecturePilot storage image."""

    def __init__(self, root: Path, *, tenant_id: str = DEFAULT_TENANT_ID) -> None:
        self.root = root
        self.tenant_id = tenant_id

    def user_key(self, user_id: str) -> str:
        return sha256(user_id.encode("utf-8")).hexdigest()[:24]

    def user_root(self, user_id: str) -> Path:
        return self.root / "users" / self.user_key(user_id)

    def user_memories_dir(self, user_id: str) -> Path:
        return self.user_root(user_id) / "memories"

    def user_course_root(self, user_id: str, course_id: str) -> Path:
        return self.user_root(user_id) / "courses" / safe_id(course_id)

    def user_lecture_root(self, user_id: str, course_id: str, lecture_id: str) -> Path:
        return self.user_course_root(user_id, course_id) / "lectures" / safe_id(lecture_id)

    def user_canvas_dir(self, user_id: str, course_id: str, lecture_id: str) -> Path:
        return self.user_lecture_root(user_id, course_id, lecture_id) / "canvas"

    def user_canvas_dir_by_key(self, user_key: str, course_id: str, lecture_id: str) -> Path:
        return (
            self.root
            / "users"
            / user_key
            / "courses"
            / safe_id(course_id)
            / "lectures"
            / safe_id(lecture_id)
            / "canvas"
        )

    def compiled_canvas_path(self, user_id: str, course_id: str, lecture_id: str) -> Path:
        return self.user_lecture_root(user_id, course_id, lecture_id) / "canvas.json"

    def legacy_user_lecture_root(self, user_id: str, course_id: str, lecture_id: str) -> Path:
        return (
            self.root
            / "workspaces"
            / "students"
            / self.user_key(user_id)
            / "courses"
            / safe_id(course_id)
            / "lectures"
            / safe_id(lecture_id)
        )

    def legacy_compiled_canvas_path(self, user_id: str, course_id: str, lecture_id: str) -> Path:
        return self.legacy_user_lecture_root(user_id, course_id, lecture_id) / "canvas.json"

    def legacy_canvas_dir_by_key(self, user_key: str, course_id: str, lecture_id: str) -> Path:
        return (
            self.root
            / "workspaces"
            / "students"
            / user_key
            / "courses"
            / safe_id(course_id)
            / "lectures"
            / safe_id(lecture_id)
            / "canvas"
        )

    def course_root(self, course_id: str) -> Path:
        return self.root / "courses" / safe_id(self.tenant_id) / safe_id(course_id)

    def course_source_root(self, course_id: str) -> Path:
        return self.course_root(course_id) / "source"

    def course_uploads_dir(self, course_id: str) -> Path:
        return self.course_source_root(course_id) / "uploads"

    def course_canvas_dir(self, course_id: str, lecture_id: str) -> Path:
        return self.course_root(course_id) / "canvas" / "lectures" / safe_id(lecture_id)

    def course_canvas_draft_dir(self, course_id: str, lecture_id: str) -> Path:
        return self.course_root(course_id) / "canvas-drafts" / "lectures" / safe_id(lecture_id) / "latest"


def safe_id(value: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "-", value).strip("-")
    if not safe:
        raise StorageLayoutError("Storage id cannot be empty.")
    return safe[:120]
