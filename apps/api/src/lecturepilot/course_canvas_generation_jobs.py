from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
import fcntl
from hashlib import sha256
import os
from pathlib import Path
from typing import Iterator, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.course_canvas_repair_target import CanvasGenerationRepairTarget
from lecturepilot.durable_files import ensure_durable_directory, fsync_directory
from lecturepilot.metadata_events import emit_metadata_event
from lecturepilot.storage_layout import StorageLayout, safe_id


GenerationStatus = Literal["running", "completed", "failed"]
MAX_TERMINAL_GENERATION_RECORDS = 256


class CanvasGenerationJob(BaseModel):
    generation_id: str = Field(min_length=32, max_length=32)
    course_id: str = Field(min_length=1, max_length=120)
    lecture_id: str = Field(min_length=1, max_length=120)
    actor_key: str = Field(min_length=24, max_length=24)
    request_key_hash: str = Field(min_length=64, max_length=64)
    status: GenerationStatus
    attempt: int = Field(ge=1)
    created_at: datetime
    updated_at: datetime
    error_code: str | None = Field(default=None, max_length=80)
    error_detail: str | None = Field(default=None, max_length=1_000)
    canvas: CanvasDocument | None = None
    repair: CanvasGenerationRepairTarget | None = None


class CanvasGenerationStoreError(RuntimeError):
    pass


class CanvasGenerationStore:
    """Atomic, private generation records in the course builder workspace."""

    def __init__(self, layout: StorageLayout, *, lease_seconds: int) -> None:
        self.layout = layout
        self.lease = timedelta(seconds=lease_seconds)

    def begin(
        self,
        *,
        course_id: str,
        lecture_id: str,
        actor_user_id: str,
        request_key: str,
    ) -> tuple[CanvasGenerationJob, bool]:
        path = self._path(course_id, lecture_id, actor_user_id, request_key)
        with self._locked(path):
            existing = self._read_path(path)
            now = datetime.now(UTC)
            if existing is None:
                job = CanvasGenerationJob(
                    generation_id=uuid4().hex,
                    course_id=course_id,
                    lecture_id=lecture_id,
                    actor_key=self.layout.user_key(actor_user_id),
                    request_key_hash=self._key_hash(actor_user_id, request_key),
                    status="running",
                    attempt=1,
                    created_at=now,
                    updated_at=now,
                )
                self._write(path, job)
                return job, True
            self._validate(existing, course_id, lecture_id, actor_user_id, request_key)
            if existing.status == "running" and now - existing.updated_at > self.lease:
                existing = existing.model_copy(
                    update={
                        "attempt": existing.attempt + 1,
                        "updated_at": now,
                        "error_code": None,
                        "error_detail": None,
                        "canvas": None,
                        "repair": None,
                    }
                )
                self._write(path, existing)
                return existing, True
            return existing, False

    def read(
        self, *, course_id: str, lecture_id: str, actor_user_id: str, request_key: str
    ) -> CanvasGenerationJob | None:
        path = self._path(course_id, lecture_id, actor_user_id, request_key)
        with self._locked(path):
            job = self._read_path(path)
            if job is not None:
                self._validate(job, course_id, lecture_id, actor_user_id, request_key)
            return job

    def complete(
        self,
        job: CanvasGenerationJob,
        canvas: CanvasDocument,
        *,
        actor_user_id: str,
        request_key: str,
    ) -> CanvasGenerationJob:
        return self._finish(
            job,
            actor_user_id=actor_user_id,
            request_key=request_key,
            status="completed",
            canvas=canvas,
        )

    def fail(
        self,
        job: CanvasGenerationJob,
        *,
        actor_user_id: str,
        request_key: str,
        error_code: str,
        error_detail: str | None = None,
        repair: CanvasGenerationRepairTarget | None = None,
    ) -> CanvasGenerationJob:
        return self._finish(
            job,
            actor_user_id=actor_user_id,
            request_key=request_key,
            status="failed",
            error_code=error_code,
            error_detail=error_detail,
            repair=repair,
        )

    def touch(
        self,
        job: CanvasGenerationJob,
        *,
        actor_user_id: str,
        request_key: str,
    ) -> CanvasGenerationJob:
        path = self._path(job.course_id, job.lecture_id, actor_user_id, request_key)
        with self._locked(path):
            current = self._read_path(path)
            if (
                current is None
                or current.generation_id != job.generation_id
                or current.attempt != job.attempt
                or current.status != "running"
            ):
                raise CanvasGenerationStoreError("Canvas generation attempt is no longer active.")
            updated = current.model_copy(update={"updated_at": datetime.now(UTC)})
            self._write(path, updated)
            return updated

    def _finish(
        self,
        job: CanvasGenerationJob,
        *,
        actor_user_id: str,
        request_key: str,
        status: GenerationStatus,
        error_code: str | None = None,
        error_detail: str | None = None,
        canvas: CanvasDocument | None = None,
        repair: CanvasGenerationRepairTarget | None = None,
    ) -> CanvasGenerationJob:
        path = self._path(job.course_id, job.lecture_id, actor_user_id, request_key)
        with self._locked(path):
            current = self._read_path(path)
            if current is None or current.generation_id != job.generation_id:
                raise CanvasGenerationStoreError("Canvas generation ownership was lost.")
            if current.attempt != job.attempt or current.status != "running":
                raise CanvasGenerationStoreError("Canvas generation attempt is no longer active.")
            updated = current.model_copy(
                update={
                    "status": status,
                    "updated_at": datetime.now(UTC),
                    "error_code": error_code,
                    "error_detail": error_detail,
                    "canvas": canvas,
                    "repair": repair,
                }
            )
            self._write(path, updated)
            self._prune_terminal_records(path)
        return updated

    def _prune_terminal_records(self, current_path: Path) -> None:
        terminal: list[tuple[Path, CanvasGenerationJob]] = []
        for path in current_path.parent.glob("*.json"):
            if path == current_path:
                continue
            try:
                job = self._read_path(path)
            except CanvasGenerationStoreError:
                continue
            if job is not None and job.status != "running":
                terminal.append((path, job))

        terminal.sort(key=lambda item: item[1].updated_at, reverse=True)
        keep_other = max(0, MAX_TERMINAL_GENERATION_RECORDS - 1)
        removed = False
        for path, _job in terminal[keep_other:]:
            try:
                path.unlink()
                removed = True
            except OSError as exc:
                emit_metadata_event(
                    "canvas_generation.retention_failed",
                    error=True,
                    exception_type=type(exc).__name__,
                )
        if removed:
            try:
                fsync_directory(current_path.parent)
            except OSError as exc:
                emit_metadata_event(
                    "canvas_generation.retention_sync_failed",
                    error=True,
                    exception_type=type(exc).__name__,
                )

    def _path(self, course_id: str, lecture_id: str, actor_user_id: str, request_key: str) -> Path:
        digest = self._key_hash(actor_user_id, request_key)
        return (
            self.layout.course_root(course_id)
            / "builder"
            / "generations"
            / safe_id(lecture_id)
            / f"{digest}.json"
        )

    @staticmethod
    def _key_hash(actor_user_id: str, request_key: str) -> str:
        return sha256(f"{actor_user_id}\0{request_key}".encode()).hexdigest()

    def _validate(
        self,
        job: CanvasGenerationJob,
        course_id: str,
        lecture_id: str,
        actor_user_id: str,
        request_key: str,
    ) -> None:
        expected = (
            course_id,
            lecture_id,
            self.layout.user_key(actor_user_id),
            self._key_hash(actor_user_id, request_key),
        )
        actual = (job.course_id, job.lecture_id, job.actor_key, job.request_key_hash)
        if actual != expected:
            raise CanvasGenerationStoreError("Canvas generation identity does not match.")

    @contextmanager
    def _locked(self, path: Path) -> Iterator[None]:
        ensure_durable_directory(path.parent)
        lock_path = path.parent / ".generation.lock"
        descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)

    @staticmethod
    def _read_path(path: Path) -> CanvasGenerationJob | None:
        if not path.exists():
            return None
        try:
            return CanvasGenerationJob.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise CanvasGenerationStoreError("Stored canvas generation state is invalid.") from exc

    @staticmethod
    def _write(path: Path, job: CanvasGenerationJob) -> None:
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
