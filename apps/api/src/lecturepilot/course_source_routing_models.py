from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class SourceRouteRole(StrEnum):
    LECTURE = "lecture"
    COURSE_WIDE = "course_wide"
    EXCLUDED = "excluded"


class SourceProcessingStatus(StrEnum):
    CONVERTED = "converted"
    OCR_NEEDED = "ocr_needed"
    PRESERVED = "preserved"


class CourseSourceRoute(BaseModel):
    path: str = Field(min_length=1, max_length=500)
    kind: str = Field(min_length=1, max_length=80)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    role: SourceRouteRole
    lecture_id: str | None = Field(default=None, max_length=120)
    processing_status: SourceProcessingStatus = SourceProcessingStatus.PRESERVED

    @model_validator(mode="after")
    def validate_lecture_assignment(self) -> "CourseSourceRoute":
        if self.role == SourceRouteRole.LECTURE and not self.lecture_id:
            raise ValueError("Lecture routes require a lecture_id.")
        if self.role != SourceRouteRole.LECTURE and self.lecture_id is not None:
            raise ValueError("Only lecture routes may include a lecture_id.")
        return self


class CourseSourceRoutingInput(BaseModel):
    source_revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    routes: list[CourseSourceRoute] = Field(max_length=5000)


class CourseSourceRoutingManifest(BaseModel):
    schema_version: Literal[2] = 2
    course_id: str = Field(min_length=1, max_length=120)
    source_revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    confirmed: bool
    routes: list[CourseSourceRoute] = Field(max_length=5000)
