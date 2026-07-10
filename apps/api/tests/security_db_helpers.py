from __future__ import annotations

from dataclasses import dataclass

from fastapi.testclient import TestClient

from lecturepilot.university_models import ExternalCourseCandidate, UniversityLoginResult


@dataclass
class FakeUniversityAdapter:
    courses_by_user: dict[str, list[ExternalCourseCandidate]]

    def login(self, *, username: str, password: str, term: str) -> UniversityLoginResult:
        assert password
        courses = self.courses_by_user.get(username, [])
        return UniversityLoginResult(
            username=username,
            email=f"{username}@example.edu",
            term=term,
            courses=courses,
            sources_checked={course.source for course in courses},
        )


def login(client: TestClient, username: str) -> dict:
    response = client.post(
        "/auth/login",
        json={"username": username, "password": "test-password", "term": "Sommer 2026"},
    )
    assert response.status_code == 200, response.json()
    return response.json()


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
