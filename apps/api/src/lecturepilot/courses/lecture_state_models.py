"""Professor-facing lifecycle state of every lecture in a course (course updates)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

RoutingState = Literal["confirmed", "needs_review"]
SourcesState = Literal["current", "changed", "new"]
GoalsState = Literal["approved", "stale", "needs_review", "proposing", "missing"]
DraftState = Literal["none", "generating", "ready", "failed", "published"]
NextAction = Literal[
    "none",
    "confirm_routing",
    "review_goals",
    "keep_or_regenerate_goals",
    "wait",
    "generate_draft",
    "retry_draft",
    "review_draft",
]

_DRAFT_ACTIONS: dict[str, NextAction] = {
    "generating": "wait",
    "failed": "retry_draft",
    "ready": "review_draft",
    "none": "generate_draft",
    "published": "none",
}


class LectureState(BaseModel):
    lecture_id: str
    number: str
    title: str
    date: date
    published: bool
    published_at: datetime | None = None
    sources: SourcesState
    goals: GoalsState
    draft: DraftState
    draft_error: str | None = Field(default=None, max_length=1_000)
    next_action: NextAction


class CourseLectureStates(BaseModel):
    course_id: str
    routing: RoutingState
    lectures: list[LectureState]


def next_action(routing: RoutingState, goals: GoalsState, draft: DraftState) -> NextAction:
    """The single most useful next step: routing first, then goals, then the draft."""
    if routing != "confirmed" and draft != "published":
        return "confirm_routing"
    if goals == "proposing":
        return "wait"
    if goals in ("missing", "needs_review"):
        return "review_goals"
    if goals == "stale":
        return "keep_or_regenerate_goals"
    return _DRAFT_ACTIONS[draft]
