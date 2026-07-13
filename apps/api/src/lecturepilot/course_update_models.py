from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from lecturepilot.models import CourseWorkspaceResult


class CourseUpdateCreated(BaseModel):
    course_id: str
    update_id: str


class CourseUpdateUploadResult(BaseModel):
    update_id: str
    path: str
    kind: str
    size_bytes: int = Field(ge=0)


class CourseUpdateFileChange(BaseModel):
    path: str = Field(min_length=1, max_length=500)
    kind: str = Field(min_length=1, max_length=80)
    size_bytes: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    status: Literal["new", "changed"]


class CourseUpdateLectureCandidate(BaseModel):
    candidate_id: str
    action: Literal["new", "update"]
    lecture_id: str | None = None
    number: str = Field(min_length=1, max_length=20)
    title: str = Field(min_length=1, max_length=200)
    date: date
    file_paths: list[str] = Field(min_length=1, max_length=500)


class CourseUpdateLectureOption(BaseModel):
    lecture_id: str
    number: str
    title: str
    date: date


class CourseUpdateAnalysis(BaseModel):
    course_id: str
    update_id: str
    candidates: list[CourseUpdateLectureCandidate]
    existing_lectures: list[CourseUpdateLectureOption]
    unassigned_files: list[CourseUpdateFileChange]
    unchanged_files: int = Field(ge=0)


class CourseUpdateLectureSelection(BaseModel):
    lecture_id: str | None = Field(default=None, max_length=120)
    number: str = Field(min_length=1, max_length=20)
    title: str = Field(min_length=1, max_length=200)
    date: date
    file_paths: list[str] = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def unique_paths(self) -> "CourseUpdateLectureSelection":
        if len(self.file_paths) != len(set(self.file_paths)):
            raise ValueError("A lecture update cannot contain duplicate file paths.")
        return self


class CourseUpdateApplyInput(BaseModel):
    lectures: list[CourseUpdateLectureSelection] = Field(min_length=1, max_length=80)

    @model_validator(mode="after")
    def unique_lectures(self) -> "CourseUpdateApplyInput":
        targets = [item.lecture_id or f"new:{item.number}" for item in self.lectures]
        if len(targets) != len(set(targets)):
            raise ValueError("Each lecture can occur only once in a course update.")
        return self


class CourseUpdateApplyResult(BaseModel):
    course_id: str
    update_id: str
    applied_files: int = Field(ge=1)
    affected_lecture_ids: list[str] = Field(min_length=1, max_length=80)
    workspace: CourseWorkspaceResult
