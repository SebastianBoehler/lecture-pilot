from __future__ import annotations

from dataclasses import dataclass, field

from fastapi.testclient import TestClient

from lecturepilot.university_models import ExternalCourseCandidate, UniversityLoginResult
from auth_helpers import pending_university_login


@dataclass
class FakeUniversityAdapter:
    courses_by_user: dict[str, list[ExternalCourseCandidate]]
    roles_by_user: dict[str, str] = field(default_factory=dict)

    def authenticate(self, *, username: str, password: str, term: str, diagnostics=None):
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
    response = client.post(
        "/auth/login",
        json={"username": username, "password": "test-password", "term": "Sommer 2026"},
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
