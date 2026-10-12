from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class UsageTotals(BaseModel):
    model_requests: int = Field(ge=0)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    cached_input_tokens: int = Field(ge=0)
    reasoning_tokens: int = Field(ge=0)
    tutor_turns: int = Field(ge=0)
    images: int = Field(ge=0)


class UsageWorkloadSummary(BaseModel):
    workload: str
    model_requests: int = Field(ge=0)
    total_tokens: int = Field(ge=0)


class UsageCourseSummary(BaseModel):
    course_id: str
    course_title: str
    model_requests: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    tutor_turns: int = Field(ge=0)
    images: int = Field(ge=0)


class UsageDailySummary(BaseModel):
    date: date
    model_requests: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    tutor_turns: int = Field(ge=0)
    images: int = Field(ge=0)


class UsageLimitSummary(BaseModel):
    turns_per_day: int = Field(gt=0)
    reserved_tokens_per_day: int = Field(gt=0)
    images_per_day: int = Field(gt=0)
    concurrent_turns: int = Field(gt=0)
    tokens_per_turn: int = Field(gt=0)


class ProfessorUsageSummary(BaseModel):
    period_start: date
    period_end: date
    totals: UsageTotals
    workloads: list[UsageWorkloadSummary]
    courses: list[UsageCourseSummary]
    daily: list[UsageDailySummary]
    limits: UsageLimitSummary
