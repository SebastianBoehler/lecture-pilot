from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from lecturepilot.exam_revision_plan import ExamReadinessAttemptResult, ExamRevisionTask
from lecturepilot.storage_layout import StorageLayout


class ReadinessProgressQuestionEvent(BaseModel):
    attempt_id: str
    question_id: str
    task_id: str | None = None
    lecture_id: str
    section_id: str
    answer_kind: str
    correct: bool | None = None
    first_try: bool
    attempt_index: int = Field(ge=1)
    status: str
    created_at: str


class ReadinessProgress(BaseModel):
    attempts: list[ReadinessProgressQuestionEvent] = Field(default_factory=list)
    active_tasks: list[ExamRevisionTask] = Field(default_factory=list)
    updated_at: str | None = None


class ReadinessProgressStore:
    def __init__(self, layout: StorageLayout) -> None:
        self.layout = layout

    def attempt_count(self, *, user_id: str, course_id: str) -> int:
        attempt_ids = {event.attempt_id for event in self.read(user_id=user_id, course_id=course_id).attempts}
        return len(attempt_ids)

    def read(self, *, user_id: str, course_id: str) -> ReadinessProgress:
        path = self._path(user_id=user_id, course_id=course_id)
        if not path.exists():
            return ReadinessProgress()
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return ReadinessProgress()
        return ReadinessProgress.model_validate(payload)

    def record_attempt(
        self,
        *,
        user_id: str,
        course_id: str,
        result: ExamReadinessAttemptResult,
    ) -> ExamReadinessAttemptResult:
        progress = self.read(user_id=user_id, course_id=course_id)
        attempt_index = self.attempt_count(user_id=user_id, course_id=course_id) + 1
        created_at = _now()
        attempt_id = f"attempt-{created_at.replace(':', '').replace('-', '').replace('+', 'Z')}"
        task_ids = {task.question_id: task.id for task in result.tasks}
        updated_result = result.model_copy(
            update={"attempt_id": attempt_id, "created_at": created_at},
            deep=True,
        )
        progress.attempts.extend(
            ReadinessProgressQuestionEvent(
                attempt_id=attempt_id,
                question_id=item.question_id,
                task_id=task_ids.get(item.question_id),
                lecture_id=item.lecture_id,
                section_id=item.section_id,
                answer_kind=item.answer_kind,
                correct=item.correct,
                first_try=not any(event.question_id == item.question_id for event in progress.attempts),
                attempt_index=attempt_index,
                status=item.status,
                created_at=created_at,
            )
            for item in updated_result.results
        )
        progress.active_tasks = updated_result.tasks
        progress.updated_at = created_at
        self._write(user_id=user_id, course_id=course_id, progress=progress)
        return updated_result

    def list_course_progress(self, *, course_id: str) -> list[tuple[str, ReadinessProgress]]:
        course_suffix = self.layout.user_course_root("__probe__", course_id).relative_to(
            self.layout.user_root("__probe__")
        )
        users_root = self.layout.root / "users"
        if not users_root.exists():
            return []
        records = []
        for user_root in users_root.iterdir():
            if not user_root.is_dir():
                continue
            path = user_root / course_suffix / "progress.json"
            if path.exists():
                records.append((user_root.name, self._read_path(path)))
        return records

    def _path(self, *, user_id: str, course_id: str) -> Path:
        return self.layout.user_course_root(user_id, course_id) / "progress.json"

    def _write(self, *, user_id: str, course_id: str, progress: ReadinessProgress) -> None:
        path = self._path(user_id=user_id, course_id=course_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(progress.model_dump(mode="json"), sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )

    def _read_path(self, path: Path) -> ReadinessProgress:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return ReadinessProgress()
        return ReadinessProgress.model_validate(payload)


def _now() -> str:
    return datetime.now(UTC).isoformat()
