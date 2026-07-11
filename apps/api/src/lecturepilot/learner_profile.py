from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from lecturepilot.user_memory import UserMemoryStore


LearningGoal = Literal["keep_up", "understand_deeply", "exam_preparation"]
_TEXT_SUFFIXES = {".json", ".jsonl", ".md", ".txt", ".yaml", ".yml"}
_MAX_PREVIEW_BYTES = 32_000


class LearnerProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    learning_goal: LearningGoal
    onboarding_completed: bool = True


class LearnerFile(BaseModel):
    path: str
    size_bytes: int = Field(ge=0)
    content: str | None = None


class LearnerCourseProfile(BaseModel):
    course_id: str
    memory: str = ""
    passed_lecture_ids: list[str] = Field(default_factory=list)
    files: list[LearnerFile] = Field(default_factory=list)


class LearnerProfileResponse(BaseModel):
    onboarding_completed: bool = False
    learning_goal: LearningGoal | None = None
    preferences: dict[str, Any] = Field(default_factory=dict)
    global_notes: str = ""
    global_files: list[LearnerFile] = Field(default_factory=list)
    courses: list[LearnerCourseProfile] = Field(default_factory=list)


def read_learner_profile(store: UserMemoryStore, user_id: str) -> LearnerProfileResponse:
    context = store.read_context(user_id)
    preferences = context.preferences
    raw_goal = preferences.get("learning_goal")
    learning_goal = (
        raw_goal if raw_goal in {"keep_up", "understand_deeply", "exam_preparation"} else None
    )
    root = store.layout.user_root(user_id)
    courses_root = root / "courses"
    return LearnerProfileResponse(
        onboarding_completed=preferences.get("onboarding_completed") is True,
        learning_goal=learning_goal,
        preferences=preferences,
        global_notes=context.global_notes,
        global_files=_files(root, include=lambda path: path.parts[0] != "courses"),
        courses=_course_profiles(courses_root),
    )


def _course_profiles(courses_root: Path) -> list[LearnerCourseProfile]:
    if not courses_root.exists() or courses_root.is_symlink():
        return []
    profiles: list[LearnerCourseProfile] = []
    for course_root in sorted(courses_root.iterdir()):
        if not course_root.is_dir() or course_root.is_symlink():
            continue
        memory_path = course_root / "memories" / "course.md"
        profiles.append(
            LearnerCourseProfile(
                course_id=course_root.name,
                memory=_read_text(memory_path, limit=4000),
                passed_lecture_ids=_passed_lecture_ids(course_root),
                files=_files(course_root),
            )
        )
    return profiles


def _files(root: Path, include=None) -> list[LearnerFile]:
    if not root.exists() or root.is_symlink():
        return []
    files: list[LearnerFile] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        relative = path.relative_to(root)
        if include and not include(relative):
            continue
        size = path.stat().st_size
        content = (
            _read_text(path, limit=_MAX_PREVIEW_BYTES)
            if path.suffix.lower() in _TEXT_SUFFIXES
            else None
        )
        files.append(LearnerFile(path=relative.as_posix(), size_bytes=size, content=content))
    return files


def _passed_lecture_ids(course_root: Path) -> list[str]:
    lectures_root = course_root / "lectures"
    if not lectures_root.exists() or lectures_root.is_symlink():
        return []
    passed: list[str] = []
    for lecture_root in sorted(lectures_root.iterdir()):
        if not lecture_root.is_dir() or lecture_root.is_symlink():
            continue
        payload = _read_json(lecture_root / "gates.json")
        gates = payload.get("gates") if isinstance(payload.get("gates"), dict) else {}
        if any(
            isinstance(gate, dict) and gate.get("status") == "passed" for gate in gates.values()
        ):
            passed.append(lecture_root.name)
    return passed


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_text(path: Path, *, limit: int) -> str:
    try:
        if path.stat().st_size > limit:
            return ""
        return path.read_text(encoding="utf-8")[:limit]
    except (FileNotFoundError, OSError, UnicodeDecodeError):
        return ""
