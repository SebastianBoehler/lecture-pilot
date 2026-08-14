from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

from lecturepilot.database import Database
from lecturepilot.db_models import ExternalIdentityRecord, TenantMembershipRecord, UserRecord
from lecturepilot.external_course_sync import sync_external_courses
from lecturepilot.identity_sync import locked_external_identity
from lecturepilot.university_models import (
    ExternalCourseSource,
    UniversityCourseSourceStatuses,
    UniversityCourseSyncStatus,
    UniversityLoginResult,
)


COURSE_SYNC_SOURCES_CLAIM = "course_sync_sources"


def record_course_sync_source(
    database: Database,
    identity: UniversityLoginResult,
    *,
    tenant_id: str,
    sync_id: str,
    source: ExternalCourseSource,
) -> bool:
    with database.session() as session:
        external = locked_external_identity(session, identity.username)
        if external is None or external.course_sync_id != sync_id:
            return False
        user = session.get(UserRecord, external.user_id)
        membership = session.get(TenantMembershipRecord, (external.user_id, tenant_id))
        if user is None or membership is None or not user.enabled:
            return False
        if identity.display_name is not None:
            user.display_name = identity.display_name
        if identity.email is not None:
            external.email = identity.email
        checked = source in identity.sources_checked
        sync_external_courses(
            session,
            user_id=user.id,
            tenant_id=tenant_id,
            observations=[course for course in identity.courses if course.source == source],
            checked_sources={source.value} if checked else set(),
        )
        statuses = source_statuses(external)
        statuses[source] = "ready" if checked else "error"
        set_source_statuses(external, statuses)
        user.updated_at = datetime.now(UTC)
        return True


def complete_course_sync(
    database: Database,
    identity: UniversityLoginResult,
    *,
    tenant_id: str,
    sync_id: str,
) -> bool:
    with database.session() as session:
        external = locked_external_identity(session, identity.username)
        if external is None or external.course_sync_id != sync_id:
            return False
        user = session.get(UserRecord, external.user_id)
        membership = session.get(TenantMembershipRecord, (external.user_id, tenant_id))
        if user is None or membership is None or not user.enabled:
            return False
        if identity.display_name is not None:
            user.display_name = identity.display_name
        if identity.email is not None:
            external.email = identity.email
        sync_external_courses(
            session,
            user_id=user.id,
            tenant_id=tenant_id,
            observations=identity.courses,
            checked_sources={source.value for source in identity.sources_checked},
        )
        external.course_sync_status = "ready" if identity.sources_checked else "error"
        set_source_statuses(
            external,
            {
                source: "ready" if source in identity.sources_checked else "error"
                for source in ExternalCourseSource
            },
        )
        external.course_sync_id = None
        user.updated_at = datetime.now(UTC)
        return True


def fail_course_sync(database: Database, *, username: str, sync_id: str) -> bool:
    with database.session() as session:
        external = locked_external_identity(session, username)
        if external is None or external.course_sync_id != sync_id:
            return False
        external.course_sync_status = "error"
        set_source_statuses(
            external,
            {
                source: "error" if status == "loading" else status
                for source, status in source_statuses(external).items()
            },
        )
        external.course_sync_id = None
        return True


def source_statuses(identity: ExternalIdentityRecord) -> UniversityCourseSourceStatuses:
    raw = identity.provider_claims.get(COURSE_SYNC_SOURCES_CLAIM, {})
    if not isinstance(raw, dict):
        return {}
    statuses: UniversityCourseSourceStatuses = {}
    for source in ExternalCourseSource:
        status = raw.get(source.value)
        if status in {"loading", "ready", "error"}:
            statuses[source] = cast(UniversityCourseSyncStatus, status)
    return statuses


def set_source_statuses(
    identity: ExternalIdentityRecord,
    statuses: UniversityCourseSourceStatuses,
) -> None:
    identity.provider_claims = {
        **identity.provider_claims,
        COURSE_SYNC_SOURCES_CLAIM: {source.value: status for source, status in statuses.items()},
    }
