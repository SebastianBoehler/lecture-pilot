from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
import fcntl
from hashlib import sha256
import os
from pathlib import Path
from typing import Iterator, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from lecturepilot.durable_files import ensure_durable_directory, fsync_directory
from lecturepilot.storage_layout import StorageLayout


PracticeExamGenerationStatus = Literal["running", "completed", "failed"]
MAX_TERMINAL_RECORDS = 128


class PracticeExamGenerationJob(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generation_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    course_id: str = Field(min_length=1, max_length=120)
    actor_key: str = Field(pattern=r"^[0-9a-f]{24}$")
    request_key_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    input_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: PracticeExamGenerationStatus
    attempt: int = Field(ge=1)
    created_at: datetime
    updated_at: datetime
    exam_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{32}$")
    error_code: str | None = Field(default=None, max_length=80)


class PracticeExamGenerationStore:
    def __init__(self, layout: StorageLayout, *, lease_seconds: int) -> None:
        self.layout = layout
        self.lease = timedelta(seconds=lease_seconds)

    def begin(
        self,
        *,
        user_id: str,
        course_id: str,
        request_key: str,
        input_hash: str,
    ) -> tuple[PracticeExamGenerationJob, bool]:
        path = self._path(user_id, course_id, request_key)
        with self._locked(path):
            existing = self._read_path(path)
            now = datetime.now(UTC)
            if existing is None:
                job = PracticeExamGenerationJob(
                    generation_id=uuid4().hex,
                    course_id=course_id,
                    actor_key=self.layout.user_key(user_id),
                    request_key_hash=self._request_hash(user_id, request_key),
                    input_hash=input_hash,
                    status="running",
                    attempt=1,
                    created_at=now,
                    updated_at=now,
                )
                self._write(path, job)
                return job, True
            self._validate(existing, user_id, course_id, request_key)
            if existing.input_hash != input_hash:
                raise ValueError("Idempotency-Key was already used with different input.")
            if existing.status == "running" and now - existing.updated_at > self.lease:
                reclaimed = existing.model_copy(
                    update={
                        "attempt": existing.attempt + 1,
                        "updated_at": now,
                        "exam_id": None,
                        "error_code": None,
                    }
                )
                self._write(path, reclaimed)
                return reclaimed, True
            return existing, False

    def read(
        self, *, user_id: str, course_id: str, request_key: str
    ) -> PracticeExamGenerationJob | None:
        path = self._path(user_id, course_id, request_key)
        with self._locked(path):
            job = self._read_path(path)
            if job:
                self._validate(job, user_id, course_id, request_key)
            return job

    def complete(
        self,
        job: PracticeExamGenerationJob,
        *,
        user_id: str,
        request_key: str,
        exam_id: str,
    ) -> PracticeExamGenerationJob:
        return self._finish(
            job, user_id=user_id, request_key=request_key, status="completed", exam_id=exam_id
        )

    def fail(
        self,
        job: PracticeExamGenerationJob,
        *,
        user_id: str,
        request_key: str,
        error_code: str,
    ) -> PracticeExamGenerationJob:
        return self._finish(
            job,
            user_id=user_id,
            request_key=request_key,
            status="failed",
            error_code=error_code,
        )

    def _finish(
        self,
        job: PracticeExamGenerationJob,
        *,
        user_id: str,
        request_key: str,
        status: PracticeExamGenerationStatus,
        exam_id: str | None = None,
        error_code: str | None = None,
    ) -> PracticeExamGenerationJob:
        path = self._path(user_id, job.course_id, request_key)
        with self._locked(path):
            current = self._read_path(path)
            if (
                current is None
                or current.generation_id != job.generation_id
                or current.attempt != job.attempt
                or current.status != "running"
            ):
                raise RuntimeError("Practice exam generation attempt is no longer active.")
            updated = current.model_copy(
                update={
                    "status": status,
                    "updated_at": datetime.now(UTC),
                    "exam_id": exam_id,
                    "error_code": error_code,
                }
            )
            self._write(path, updated)
            self._prune(path)
            return updated

    def _prune(self, current_path: Path) -> None:
        terminal = []
        for path in current_path.parent.glob("*.json"):
            job = self._read_path(path)
            if path != current_path and job and job.status != "running":
                terminal.append((path, job.updated_at))
        terminal.sort(key=lambda item: item[1], reverse=True)
        for path, _updated_at in terminal[max(0, MAX_TERMINAL_RECORDS - 1) :]:
            path.unlink(missing_ok=True)
        fsync_directory(current_path.parent)

    def _path(self, user_id: str, course_id: str, request_key: str) -> Path:
        return self.layout.practice_exam_generations_dir(user_id, course_id) / (
            f"{self._request_hash(user_id, request_key)}.json"
        )

    def _validate(
        self, job: PracticeExamGenerationJob, user_id: str, course_id: str, request_key: str
    ) -> None:
        if (
            job.course_id != course_id
            or job.actor_key != self.layout.user_key(user_id)
            or job.request_key_hash != self._request_hash(user_id, request_key)
        ):
            raise RuntimeError("Practice exam generation identity does not match.")

    @staticmethod
    def _request_hash(user_id: str, request_key: str) -> str:
        return sha256(f"{user_id}\0{request_key}".encode()).hexdigest()

    @contextmanager
    def _locked(self, path: Path) -> Iterator[None]:
        ensure_durable_directory(path.parent)
        descriptor = os.open(path.parent / ".generation.lock", os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)

    @staticmethod
    def _read_path(path: Path) -> PracticeExamGenerationJob | None:
        if not path.is_file():
            return None
        return PracticeExamGenerationJob.model_validate_json(path.read_text(encoding="utf-8"))

    @staticmethod
    def _write(path: Path, job: PracticeExamGenerationJob) -> None:
        temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
        try:
            descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(job.model_dump_json())
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
            fsync_directory(path.parent)
        finally:
            temporary.unlink(missing_ok=True)
