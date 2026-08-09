from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field


class GateReviewQueueItem(BaseModel):
    id: str
    kind: Literal["gate_review", "gate_repair"]
    course_id: str
    lecture_id: str
    lecture_title: str
    section_id: str
    section_title: str
    gate_id: str
    gate_revision: str
    due_at: str


class ReadinessReviewQueueItem(BaseModel):
    id: str
    kind: Literal["readiness_repair"] = "readiness_repair"
    course_id: str
    lecture_id: str
    lecture_title: str
    section_id: str
    section_title: str
    task_id: str
    next_action: str


ReviewQueueItem = Annotated[
    GateReviewQueueItem | ReadinessReviewQueueItem,
    Field(discriminator="kind"),
]


class CourseReviewQueue(BaseModel):
    course_id: str
    items: list[ReviewQueueItem] = Field(default_factory=list)


class GateReviewOpening(BaseModel):
    course_id: str
    lecture_id: str
    section_id: str
    gate_id: str
    gate_revision: str
    prompt: str
    stage: Literal["due", "repair"]
