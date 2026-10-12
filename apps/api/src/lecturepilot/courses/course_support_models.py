from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from lecturepilot.courses.university_models import ExternalCourseSource


class CourseSupportKey(BaseModel):
    """Identifies one of the session user's own stored Alma/ILIAS course observations."""

    model_config = ConfigDict(extra="forbid")

    source: ExternalCourseSource
    external_course_id: str = Field(min_length=1, max_length=240)
    term: str = Field(min_length=1, max_length=80)


class CourseSupportStatus(CourseSupportKey):
    requested: bool
    # Distinct accounts in the tenant, including the caller when `requested` is true.
    request_count: int = Field(ge=0)


class CourseSupportStatusList(BaseModel):
    items: list[CourseSupportStatus]


class CourseSupportDemandRow(CourseSupportKey):
    """Aggregate demand for one university course; never carries account identities."""

    title: str
    number: str | None = None
    organization: str | None = None
    instructor: str | None = None
    display_url: str | None = None
    request_count: int = Field(ge=0)
    enrolled_user_count: int = Field(ge=0)
    has_workspace: bool
    first_requested_at: datetime | None = None
    last_requested_at: datetime | None = None


class CourseSupportDemand(BaseModel):
    items: list[CourseSupportDemandRow]


class CourseSupportMatch(BaseModel):
    request_count: int = Field(ge=0)
    enrolled_user_count: int = Field(ge=0)
