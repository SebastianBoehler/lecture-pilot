from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
import os
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, Field, ValidationError

from lecturepilot.durable_files import ensure_durable_directory, fsync_directory
from lecturepilot.lecture_source_manifest import read_lecture_source_manifest
from lecturepilot.storage_layout import StorageLayout


class CanvasRepairRecord(BaseModel):
    schema_version: int = 1
    course_id: str = Field(min_length=1, max_length=120)
    lecture_id: str = Field(min_length=1, max_length=120)
    source_revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    failure_code: str = Field(min_length=1, max_length=80)
    failure_detail: str = Field(min_length=1, max_length=1_000)
    repaired_generation_id: str = Field(min_length=32, max_length=32)
    repaired_at: datetime


def matching_repair_guidance(
    layout: StorageLayout,
    *,
    course_id: str,
    lecture_id: str,
) -> CanvasRepairRecord | None:
    revision = lecture_source_revision(layout, course_id=course_id, lecture_id=lecture_id)
    if revision is None:
        return None
    record = _read_record(layout.lecture_canvas_repair_path(course_id, lecture_id))
    if record is None or record.source_revision != revision:
        return None
    return record


def persist_repair_guidance(
    layout: StorageLayout,
    *,
    course_id: str,
    lecture_id: str,
    failure_code: str,
    failure_detail: str,
    generation_id: str,
) -> CanvasRepairRecord:
    revision = lecture_source_revision(layout, course_id=course_id, lecture_id=lecture_id)
    if revision is None:
        raise ValueError("Lecture source revision is unavailable for repair persistence.")
    record = CanvasRepairRecord(
        course_id=course_id,
        lecture_id=lecture_id,
        source_revision=revision,
        failure_code=failure_code,
        failure_detail=failure_detail,
        repaired_generation_id=generation_id,
        repaired_at=datetime.now(UTC),
    )
    _atomic_write(
        layout.lecture_canvas_repair_path(course_id, lecture_id),
        record.model_dump_json(indent=2),
    )
    return record


def lecture_source_revision(
    layout: StorageLayout,
    *,
    course_id: str,
    lecture_id: str,
) -> str | None:
    manifest = read_lecture_source_manifest(
        layout.lecture_source_manifest_path(course_id, lecture_id),
        course_id,
        lecture_id,
    )
    if not manifest.files:
        return None
    material = "\n".join(
        f"{item.path}\0{item.sha256}" for item in sorted(manifest.files, key=lambda item: item.path)
    )
    return sha256(material.encode()).hexdigest()


def _read_record(path: Path) -> CanvasRepairRecord | None:
    if not path.exists():
        return None
    try:
        return CanvasRepairRecord.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError):
        return None


def _atomic_write(path: Path, content: str) -> None:
    ensure_durable_directory(path.parent)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)
