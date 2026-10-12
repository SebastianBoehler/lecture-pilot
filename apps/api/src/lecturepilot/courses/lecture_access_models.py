from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CourseAccessPolicy(StrEnum):
    PUBLIC = "public"
    PLATFORM_AUTHENTICATED = "platform_authenticated"
    TUEBINGEN_ENROLLED = "tuebingen_enrolled"
    INSTRUCTORS_ONLY = "instructors_only"


class PublicationMode(StrEnum):
    HIDDEN = "hidden"
    ON_LECTURE_DATE = "on_lecture_date"
    CUSTOM = "custom"
    PUBLISHED_NOW = "published_now"


class LectureReleaseStatus(StrEnum):
    HIDDEN = "hidden"
    SCHEDULED = "scheduled"
    RELEASED = "released"


class LectureAccessRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    audience: CourseAccessPolicy = CourseAccessPolicy.TUEBINGEN_ENROLLED
    publication_mode: PublicationMode = PublicationMode.ON_LECTURE_DATE
    publication_at: datetime | None = None

    @model_validator(mode="after")
    def valid_publication_time(self) -> "LectureAccessRule":
        timed = self.publication_mode in {
            PublicationMode.CUSTOM,
            PublicationMode.PUBLISHED_NOW,
        }
        if timed and not _is_aware(self.publication_at):
            raise ValueError("Custom and immediate publication require a timezone-aware time.")
        if not timed and self.publication_at is not None:
            raise ValueError("This publication mode does not accept a publication time.")
        return self


class LectureAccessRuleInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    audience: CourseAccessPolicy
    publication_mode: PublicationMode
    publication_at: datetime | None = None

    @model_validator(mode="after")
    def valid_input(self) -> "LectureAccessRuleInput":
        if self.publication_mode is PublicationMode.CUSTOM:
            if not _is_aware(self.publication_at):
                raise ValueError("Custom publication requires a timezone-aware publication_at.")
        elif self.publication_at is not None:
            raise ValueError("publication_at is accepted only for custom publication.")
        return self

    def materialize(self, *, now: datetime | None = None) -> LectureAccessRule:
        publication_at = self.publication_at
        if self.publication_mode is PublicationMode.PUBLISHED_NOW:
            publication_at = now or datetime.now(UTC)
        return LectureAccessRule(
            audience=self.audience,
            publication_mode=self.publication_mode,
            publication_at=publication_at,
        )


class LectureAccessUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule: LectureAccessRuleInput
    confirm_university_members: bool = False


class LectureAccessSummary(BaseModel):
    lecture_id: str = Field(min_length=1, max_length=120)
    rule_source: Literal["course_default", "lecture_override"]
    rule: LectureAccessRule
    effective_publication_at: datetime | None = None
    release_status: LectureReleaseStatus
    content_ready: bool


class CourseAccessSummary(BaseModel):
    course_id: str = Field(min_length=1, max_length=120)
    default_rule: LectureAccessRule
    lectures: list[LectureAccessSummary]


def _is_aware(value: datetime | None) -> bool:
    return value is not None and value.tzinfo is not None and value.utcoffset() is not None
