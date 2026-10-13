"""Contracts and private builder records of professor change requests.

Records live below `builder/change-requests/<lecture-id>/` for the professor only: they are
never part of a canvas, a learner view or professor analytics.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError

from lecturepilot.core.durable_files import atomic_write_text
from lecturepilot.core.storage_layout import StorageLayout, safe_id

MAX_CHANGE_INSTRUCTION = 2_000
_SectionId = Annotated[str, StringConstraints(min_length=1, max_length=120)]


class CanvasChangeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instruction: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_CHANGE_INSTRUCTION),
    ]
    section_ids: list[_SectionId] = Field(default_factory=list, max_length=50)

    def named_sections(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(self.section_ids))


class CanvasChangeSection(BaseModel):
    id: str
    title: str


class CanvasChangeRecord(BaseModel):
    schema_version: Literal[1] = 1
    generation_id: str = Field(min_length=32, max_length=32)
    base: Literal["draft", "published"]
    instruction: str = Field(max_length=MAX_CHANGE_INSTRUCTION)
    section_ids: list[str]
    selection: Literal["professor", "automatic"]
    reasons: dict[str, str] = Field(default_factory=dict)
    requested_at: datetime


class CanvasChangeOptions(BaseModel):
    base: Literal["draft", "published"]
    sections: list[CanvasChangeSection]
    latest: CanvasChangeRecord | None = None


def write_change_record(
    layout: StorageLayout, *, course_id: str, lecture_id: str, record: CanvasChangeRecord
) -> None:
    path = _directory(layout, course_id, lecture_id) / f"{record.generation_id}.json"
    atomic_write_text(path, record.model_dump_json(indent=2))


def latest_change_record(
    layout: StorageLayout, *, course_id: str, lecture_id: str
) -> CanvasChangeRecord | None:
    directory = _directory(layout, course_id, lecture_id)
    records = []
    for path in directory.glob("*.json") if directory.is_dir() else ():
        try:
            records.append(CanvasChangeRecord.model_validate_json(path.read_text("utf-8")))
        except (OSError, ValidationError):
            continue
    return max(records, key=lambda record: record.requested_at, default=None)


def change_record(**fields) -> CanvasChangeRecord:
    return CanvasChangeRecord(requested_at=datetime.now(UTC), **fields)


def _directory(layout: StorageLayout, course_id: str, lecture_id: str):
    return layout.course_root(course_id) / "builder" / "change-requests" / safe_id(lecture_id)
