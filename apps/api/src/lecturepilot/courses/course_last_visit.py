"""Per-learner course visit markers for "new since your last visit" badges.

Stored privately at ``users/<user-key>/courses/<course-id>/last-visit.json``. A visit that
follows the previous one within ``VISIT_SESSION_GAP`` extends the same session, so reloads do
not clear badges. A badge clears once the learner opens that lecture.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

from pydantic import AwareDatetime, BaseModel, Field, ValidationError

from lecturepilot.core.durable_files import atomic_write_json, exclusive_file_lock
from lecturepilot.core.storage_layout import StorageLayout

VISIT_SESSION_GAP = timedelta(minutes=30)
MAX_TRACKED_LECTURES = 500


class CourseVisitState(BaseModel):
    schema_version: Literal[1] = 1
    course_id: str
    previous_visit_at: AwareDatetime | None = None
    current_visit_at: AwareDatetime | None = None
    opened_lectures: dict[str, AwareDatetime] = Field(default_factory=dict)


class CourseVisitResult(BaseModel):
    course_id: str
    previous_visit_at: datetime | None = None
    new_lecture_ids: list[str] = Field(default_factory=list)


@dataclass(frozen=True)
class ReleasedLecture:
    id: str
    released_at: datetime


class CourseVisitStore:
    def __init__(self, layout: StorageLayout) -> None:
        self.layout = layout

    def record_course_visit(
        self, *, user_id: str, course_id: str, now: datetime | None = None
    ) -> CourseVisitState:
        current = now or datetime.now(UTC)
        path = self._path(user_id, course_id)
        with exclusive_file_lock(path):
            state = _read(path, course_id)
            last = state.current_visit_at
            if last is None:
                state = state.model_copy(update={"current_visit_at": current})
            elif current - last >= VISIT_SESSION_GAP:
                state = state.model_copy(
                    update={"previous_visit_at": last, "current_visit_at": current}
                )
            else:
                state = state.model_copy(update={"current_visit_at": max(last, current)})
            _write(path, state)
            return state

    def record_lecture_opened(
        self, *, user_id: str, course_id: str, lecture_id: str, now: datetime | None = None
    ) -> None:
        path = self._path(user_id, course_id)
        with exclusive_file_lock(path):
            state = _read(path, course_id)
            opened = dict(state.opened_lectures)
            opened.pop(lecture_id, None)
            opened[lecture_id] = now or datetime.now(UTC)
            while len(opened) > MAX_TRACKED_LECTURES:
                opened.pop(next(iter(opened)))
            _write(path, state.model_copy(update={"opened_lectures": opened}))

    def _path(self, user_id: str, course_id: str) -> Path:
        return self.layout.user_course_root(user_id, course_id) / "last-visit.json"


def new_lecture_ids(state: CourseVisitState, lectures: list[ReleasedLecture]) -> list[str]:
    baseline = state.previous_visit_at
    if baseline is None:
        return []
    result = []
    for lecture in lectures:
        if lecture.released_at <= baseline:
            continue
        opened_at = state.opened_lectures.get(lecture.id)
        if opened_at is None or opened_at < lecture.released_at:
            result.append(lecture.id)
    return result


def _read(path: Path, course_id: str) -> CourseVisitState:
    try:
        state = CourseVisitState.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError, ValidationError):
        return CourseVisitState(course_id=course_id)
    return state if state.course_id == course_id else CourseVisitState(course_id=course_id)


def _write(path: Path, state: CourseVisitState) -> None:
    atomic_write_json(path, state.model_dump(mode="json"))
