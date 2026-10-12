from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class _Selection(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    path: str = Field(min_length=1, max_length=500)


class LectureSelection(_Selection):
    role: Literal["lecture"]
    lecture_id: str = Field(min_length=1, max_length=120)


class CourseSelection(_Selection):
    role: Literal["course_wide"]
    lecture_id: None


class ExcludedSelection(_Selection):
    role: Literal["excluded"]
    lecture_id: None


class SourceRoutingProposal(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    selections: list[LectureSelection | CourseSelection]


class SourceRoutingReview(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    corrections: list[LectureSelection | CourseSelection | ExcludedSelection]
