from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints


AlmaRole = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=120),
]


class ExternalCourseSource(StrEnum):
    ALMA = "alma"
    ILIAS = "ilias"


class ExternalCourseCandidate(BaseModel):
    source: ExternalCourseSource
    external_course_id: str = Field(min_length=1, max_length=240)
    term: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=200)
    number: str | None = Field(default=None, max_length=80)
    organization: str | None = Field(default=None, max_length=200)
    instructor: str | None = Field(default=None, max_length=200)
    display_url: str | None = Field(default=None, max_length=700)


class UniversityLoginResult(BaseModel):
    username: str = Field(min_length=1, max_length=200)
    display_name: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=320)
    term: str = Field(min_length=1, max_length=80)
    alma_current_role: AlmaRole | None = None
    alma_available_roles: list[AlmaRole] = Field(default_factory=list, max_length=24)
    courses: list[ExternalCourseCandidate] = Field(default_factory=list)
    sources_checked: set[ExternalCourseSource] = Field(default_factory=set)
    warnings: list[str] = Field(default_factory=list)
