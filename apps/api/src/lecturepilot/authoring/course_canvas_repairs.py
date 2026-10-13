from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from lecturepilot.core.durable_files import atomic_write_text
from lecturepilot.core.storage_layout import StorageLayout
from lecturepilot.sources.lecture_source_revision import (
    lecture_source_revision as lecture_source_revision,
)


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
    atomic_write_text(
        layout.lecture_canvas_repair_path(course_id, lecture_id),
        record.model_dump_json(indent=2),
    )
    return record


def _read_record(path: Path) -> CanvasRepairRecord | None:
    if not path.exists():
        return None
    try:
        return CanvasRepairRecord.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError):
        return None
