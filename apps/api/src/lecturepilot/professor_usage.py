from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID

from sqlalchemy import select

from lecturepilot.database import Database
from lecturepilot.db_models import CourseRecord, ModelUsageEventRecord, UsageCounterRecord
from lecturepilot.usage_models import (
    ProfessorUsageSummary,
    UsageCourseSummary,
    UsageDailySummary,
    UsageLimitSummary,
    UsageTotals,
    UsageWorkloadSummary,
)
from lecturepilot.usage_quota import UsageLimits


class ProfessorUsageRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def summary(
        self,
        *,
        actor_user_id: str,
        tenant_id: str,
        days: int,
    ) -> ProfessorUsageSummary:
        today = date.today()
        start = today - timedelta(days=days - 1)
        limits = UsageLimits.from_env()
        if not self.database.configured:
            return _empty_summary(start, today, limits)
        try:
            actor_id = UUID(actor_user_id)
        except ValueError:
            return _empty_summary(start, today, limits)
        with self.database.session() as session:
            courses = session.scalars(
                select(CourseRecord)
                .where(
                    CourseRecord.tenant_id == tenant_id,
                    CourseRecord.owner_user_id == actor_id,
                )
                .order_by(CourseRecord.created_at)
            ).all()
            course_ids = [course.id for course in courses]
            if not course_ids:
                return _empty_summary(start, today, limits)
            events = session.scalars(
                select(ModelUsageEventRecord).where(
                    ModelUsageEventRecord.tenant_id == tenant_id,
                    ModelUsageEventRecord.course_id.in_(course_ids),
                    ModelUsageEventRecord.created_at
                    >= datetime.combine(start, time.min, tzinfo=UTC),
                )
            ).all()
            counters = session.scalars(
                select(UsageCounterRecord).where(
                    UsageCounterRecord.tenant_id == tenant_id,
                    UsageCounterRecord.course_id.in_([str(course_id) for course_id in course_ids]),
                    UsageCounterRecord.usage_date >= start,
                )
            ).all()
        return _aggregate(start, today, limits, courses, events, counters)


def _aggregate(start, today, limits, courses, events, counters) -> ProfessorUsageSummary:
    totals = _totals()
    by_course = {course.id: _activity() for course in courses}
    by_workload: dict[str, dict[str, int]] = {}
    by_day: dict[date, dict[str, int]] = {}
    for event in events:
        _add_event(totals, event)
        _add_event(by_course[event.course_id], event)
        _add_event(by_workload.setdefault(event.workload, _activity()), event)
        _add_event(by_day.setdefault(event.created_at.date(), _activity()), event)
    for counter in counters:
        try:
            course_id = UUID(counter.course_id)
        except ValueError:
            continue
        activity = by_course.get(course_id)
        if activity is None:
            continue
        for target in (totals, activity, by_day.setdefault(counter.usage_date, _activity())):
            target["tutor_turns"] += counter.agent_turns
            target["images"] += counter.images
    return ProfessorUsageSummary(
        period_start=start,
        period_end=today,
        totals=UsageTotals(**totals),
        workloads=[
            UsageWorkloadSummary(
                workload=name,
                model_requests=values["model_requests"],
                total_tokens=values["total_tokens"],
            )
            for name, values in sorted(by_workload.items())
        ],
        courses=[
            UsageCourseSummary(
                course_id=str(course.id),
                course_title=course.title,
                **_activity_fields(by_course[course.id]),
            )
            for course in courses
        ],
        daily=[
            UsageDailySummary(date=day, **_activity_fields(values))
            for day, values in sorted(by_day.items())
        ],
        limits=UsageLimitSummary(**limits.__dict__),
    )


def _empty_summary(start: date, today: date, limits: UsageLimits) -> ProfessorUsageSummary:
    return ProfessorUsageSummary(
        period_start=start,
        period_end=today,
        totals=UsageTotals(**_totals()),
        workloads=[],
        courses=[],
        daily=[],
        limits=UsageLimitSummary(**limits.__dict__),
    )


def _totals() -> dict[str, int]:
    return {
        **_activity(),
        "input_tokens": 0,
        "output_tokens": 0,
        "cached_input_tokens": 0,
        "reasoning_tokens": 0,
    }


def _activity() -> dict[str, int]:
    return {"model_requests": 0, "total_tokens": 0, "tutor_turns": 0, "images": 0}


def _activity_fields(values: dict[str, int]) -> dict[str, int]:
    return {name: values[name] for name in _activity()}


def _add_event(target: dict[str, int], event: ModelUsageEventRecord) -> None:
    target["model_requests"] += 1
    target["total_tokens"] += event.total_tokens
    for name in ("input_tokens", "output_tokens", "cached_input_tokens", "reasoning_tokens"):
        if name in target:
            target[name] += getattr(event, name)
