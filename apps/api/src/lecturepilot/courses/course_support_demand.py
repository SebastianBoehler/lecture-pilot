from __future__ import annotations

from sqlalchemy import and_, desc, distinct, exists, func, select, tuple_

from lecturepilot.core.db_models import CourseExternalRefRecord
from lecturepilot.courses.course_support_models import CourseSupportDemandRow, CourseSupportMatch
from lecturepilot.courses.course_support_requests import Observation, Request, tenant_member_ids
from lecturepilot.courses.external_course_sync import course_title_key
from lecturepilot.database import Database


def course_support_demand(
    database: Database, *, tenant_id: str, limit: int
) -> list[CourseSupportDemandRow]:
    """Every course observed for tenant members, with request and enrollment counts only."""
    members = tenant_member_ids(tenant_id)
    latest = (
        select(
            Observation.source,
            Observation.external_course_id,
            Observation.term,
            Observation.title,
            Observation.number,
            Observation.organization,
            Observation.instructor,
            Observation.display_url,
            func.row_number()
            .over(
                partition_by=(
                    Observation.source,
                    Observation.external_course_id,
                    Observation.term,
                ),
                order_by=(Observation.observed_at.desc(), Observation.id),
            )
            .label("rank"),
        )
        .where(Observation.user_id.in_(members))
        .subquery()
    )
    enrolled = (
        select(
            Observation.source,
            Observation.external_course_id,
            Observation.term,
            func.count(distinct(Observation.user_id)).label("enrolled"),
        )
        .where(Observation.user_id.in_(members))
        .group_by(Observation.source, Observation.external_course_id, Observation.term)
        .subquery()
    )
    requested = (
        select(
            Request.source,
            Request.external_course_id,
            Request.term,
            func.count(distinct(Request.user_id)).label("requests"),
            func.min(Request.created_at).label("first_requested_at"),
            func.max(Request.created_at).label("last_requested_at"),
        )
        .where(Request.user_id.in_(members))
        .group_by(Request.source, Request.external_course_id, Request.term)
        .subquery()
    )
    request_count = func.coalesce(requested.c.requests, 0)
    has_workspace = exists().where(
        CourseExternalRefRecord.tenant_id == tenant_id,
        CourseExternalRefRecord.source == latest.c.source,
        CourseExternalRefRecord.external_course_id == latest.c.external_course_id,
        CourseExternalRefRecord.term == latest.c.term,
    )
    query = (
        select(
            latest.c.source,
            latest.c.external_course_id,
            latest.c.term,
            latest.c.title,
            latest.c.number,
            latest.c.organization,
            latest.c.instructor,
            latest.c.display_url,
            request_count.label("request_count"),
            enrolled.c.enrolled.label("enrolled_user_count"),
            has_workspace.label("has_workspace"),
            requested.c.first_requested_at,
            requested.c.last_requested_at,
        )
        .join(enrolled, _same_course(latest, enrolled))
        .outerjoin(requested, _same_course(latest, requested))
        .where(latest.c.rank == 1)
        .order_by(desc(request_count), desc(enrolled.c.enrolled), latest.c.title)
        .limit(limit)
    )
    with database.session() as session:
        rows = session.execute(query).mappings().all()
    return [CourseSupportDemandRow(**row) for row in rows]


def course_support_match(
    database: Database, *, tenant_id: str, title: str, term: str | None
) -> CourseSupportMatch:
    """Aggregate demand for observed courses whose title key (and term) match the given course."""
    target = course_title_key(title)
    if not target:
        return CourseSupportMatch(request_count=0, enrolled_user_count=0)
    members = tenant_member_ids(tenant_id)
    candidates = select(
        Observation.source, Observation.external_course_id, Observation.term, Observation.title
    ).where(Observation.user_id.in_(members))
    if term and term.strip():
        candidates = candidates.where(func.lower(Observation.term) == term.strip().lower())
    with database.session() as session:
        keys = {
            (source, course_id, course_term)
            for source, course_id, course_term, course_title in session.execute(
                candidates.distinct()
            )
            if course_title_key(course_title) == target
        }
        if not keys:
            return CourseSupportMatch(request_count=0, enrolled_user_count=0)
        requests = session.scalar(
            select(func.count(distinct(Request.user_id))).where(
                Request.user_id.in_(members),
                tuple_(Request.source, Request.external_course_id, Request.term).in_(keys),
            )
        )
        enrolled = session.scalar(
            select(func.count(distinct(Observation.user_id))).where(
                Observation.user_id.in_(members),
                tuple_(Observation.source, Observation.external_course_id, Observation.term).in_(
                    keys
                ),
            )
        )
    return CourseSupportMatch(request_count=requests or 0, enrolled_user_count=enrolled or 0)


def _same_course(left, right):
    return and_(
        left.c.source == right.c.source,
        left.c.external_course_id == right.c.external_course_id,
        left.c.term == right.c.term,
    )
