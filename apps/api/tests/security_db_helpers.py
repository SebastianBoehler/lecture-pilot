from __future__ import annotations

from dataclasses import dataclass, field

from fastapi.testclient import TestClient

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from lecturepilot.core.db_models import (
    CourseEnrollmentRecord,
    CourseExternalRefRecord,
    ExternalCourseObservationRecord,
    ExternalIdentityRecord,
    TenantMembershipRecord,
    UserRecord,
)
from lecturepilot.courses.university_models import ExternalCourseCandidate
from lecturepilot.identity.identity_roles import (
    ALMA_AVAILABLE_ROLES_CLAIM,
    ALMA_CURRENT_ROLE_CLAIM,
)
from lecturepilot.identity.identity_repository import AccountView, IdentityRepository
from lecturepilot.identity.local_account_models import LocalCredentialRecord
from lecturepilot.identity.local_passwords import hash_password

TENANT_ID = "tenant-tuebingen"


@dataclass
class LegacyUniversityAccounts:
    """Accounts that existed before the email login: Alma role, observed courses, enrollments."""

    courses_by_user: dict[str, list[ExternalCourseCandidate]]
    roles_by_user: dict[str, str] = field(default_factory=dict)


def login(client: TestClient, username: str) -> dict:
    email = f"{username}@uni-tuebingen.de"
    _seed_legacy_account(client, username, email)
    response = client.post("/auth/login", json={"email": email, "password": "test-password"})
    assert response.status_code == 200, response.json()
    current = client.get("/me")
    assert current.status_code == 200, current.json()
    account = current.json()
    if account.get("csrf_token") is None:
        account.pop("csrf_token", None)
    return {**response.json(), **account}


def _seed_legacy_account(client: TestClient, username: str, email: str) -> None:
    """Write the rows a pre-email university login left behind; enrollments follow course refs."""
    fixtures = client.app.state.legacy_accounts
    account = seed_account(
        client.app.state.database,
        username,
        role=fixtures.roles_by_user.get(username, "student"),
        email=email,
    )
    with client.app.state.database.session() as db:
        now = datetime.now(UTC)
        for course in fixtures.courses_by_user.get(username, []):
            _seed_observed_course(db, account.user_id, course, now)


def seed_account(
    database, username: str, *, role: str = "student", email: str | None = None
) -> AccountView:
    """Create or update a legacy university account with an Alma role and a test password."""
    email = email or f"{username}@uni-tuebingen.de"
    with database.session() as db:
        identity = db.scalar(
            select(ExternalIdentityRecord).where(
                ExternalIdentityRecord.provider == "tuebingen",
                ExternalIdentityRecord.subject == username,
            )
        )
        if identity is None:
            user = UserRecord()
            db.add(user)
            db.flush()
            identity = ExternalIdentityRecord(
                user_id=user.id, provider="tuebingen", subject=username
            )
            db.add(identity)
            db.add(TenantMembershipRecord(user_id=user.id, tenant_id=TENANT_ID))
            db.add(
                LocalCredentialRecord(
                    email=email, user_id=user.id, password_hash=hash_password("test-password")
                )
            )
        identity.email = email
        identity.provider_claims = {
            ALMA_CURRENT_ROLE_CLAIM: role,
            ALMA_AVAILABLE_ROLES_CLAIM: [role],
        }
        identity.last_login_at = datetime.now(UTC)
        user_id = identity.user_id
    account = IdentityRepository(database).account(user_id=user_id, tenant_id=TENANT_ID)
    assert account is not None
    return account


def _seed_observed_course(db, user_id, course: ExternalCourseCandidate, now: datetime) -> None:
    source = course.source.value
    observation = db.scalar(
        select(ExternalCourseObservationRecord).where(
            ExternalCourseObservationRecord.user_id == user_id,
            ExternalCourseObservationRecord.source == source,
            ExternalCourseObservationRecord.external_course_id == course.external_course_id,
            ExternalCourseObservationRecord.term == course.term,
        )
    )
    if observation is not None:
        observation.observed_at = now
        return
    values = course.model_dump(mode="json")
    values.pop("source")
    db.add(
        ExternalCourseObservationRecord(user_id=user_id, source=source, observed_at=now, **values)
    )
    ref = db.scalar(
        select(CourseExternalRefRecord).where(
            CourseExternalRefRecord.tenant_id == TENANT_ID,
            CourseExternalRefRecord.source == course.source.value,
            CourseExternalRefRecord.external_course_id == course.external_course_id,
            CourseExternalRefRecord.term == course.term,
        )
    )
    if ref is not None:
        db.add(
            CourseEnrollmentRecord(
                course_id=ref.course_id,
                user_id=user_id,
                source=course.source.value,
                external_course_id=course.external_course_id,
                status="active",
            )
        )


def seed_course_ref(database, course_id: str, course: ExternalCourseCandidate) -> None:
    """Link a course to an Alma/ILIAS course the way pre-email logins did by title match."""
    with database.session() as db:
        db.add(
            CourseExternalRefRecord(
                course_id=UUID(course_id),
                tenant_id=TENANT_ID,
                source=course.source.value,
                external_course_id=course.external_course_id,
                term=course.term,
                number=course.number,
                title=course.title,
                instructor=course.instructor,
            )
        )


def mutation_headers(session: dict) -> dict[str, str]:
    return {
        "Origin": "http://localhost:8000",
        "X-CSRF-Token": session["csrf_token"],
    }


def candidate(
    source: str,
    identifier: str,
    *,
    title: str = "Secure Systems",
    term: str = "Sommer 2026",
) -> ExternalCourseCandidate:
    return ExternalCourseCandidate(
        source=source,
        external_course_id=identifier,
        term=term,
        number="SEC-1",
        title=title,
        instructor="Professor Example",
    )
