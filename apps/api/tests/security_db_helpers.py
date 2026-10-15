from __future__ import annotations

from dataclasses import dataclass, field

from fastapi.testclient import TestClient

from lecturepilot.courses.university_models import ExternalCourseCandidate, UniversityLoginResult
from auth_helpers import pending_university_login


@dataclass
class FakeUniversityAdapter:
    courses_by_user: dict[str, list[ExternalCourseCandidate]]
    roles_by_user: dict[str, str] = field(default_factory=dict)

    def authenticate(self, *, username: str, password: str, term: str):
        assert password
        courses = self.courses_by_user.get(username, [])
        return pending_university_login(
            UniversityLoginResult(
                username=username,
                email=f"{username}@example.edu",
                term=term,
                alma_current_role=self.roles_by_user.get(username, "student"),
                alma_available_roles=[self.roles_by_user.get(username, "student")],
                courses=courses,
                sources_checked={course.source for course in courses},
            )
        )


def login(client: TestClient, username: str) -> dict:
    # Seed trusted historical identity/enrollment fixtures independently of HTTP authentication.
    from lecturepilot.identity.identity_repository import IdentityRepository
    from lecturepilot.identity.local_account_models import LocalCredentialRecord
    from lecturepilot.identity.local_passwords import hash_password

    adapter = client.app.state.tuebingen_adapter
    pending = adapter.authenticate(username=username, password="test-password", term="Sommer 2026")
    identity = pending.synchronize()
    identity = identity.model_copy(update={"email": f"{username}@uni-tuebingen.de"})
    account = IdentityRepository(client.app.state.database).record_login(
        identity,
        tenant_id="tenant-tuebingen",
    )
    with client.app.state.database.session() as db:
        credential = db.get(LocalCredentialRecord, identity.email)
        if credential is None:
            db.add(
                LocalCredentialRecord(
                    email=identity.email,
                    user_id=account.user_id,
                    password_hash=hash_password("test-password"),
                )
            )
    response = client.post(
        "/auth/login",
        json={"email": identity.email, "password": "test-password"},
    )
    assert response.status_code == 200, response.json()
    current = client.get("/me")
    assert current.status_code == 200, current.json()
    account = current.json()
    if account.get("csrf_token") is None:
        account.pop("csrf_token", None)
    return {**response.json(), **account}


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
