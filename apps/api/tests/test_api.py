from fastapi.testclient import TestClient

from lecturepilot.app import create_app
from lecturepilot.session_auth import SESSION_COOKIE_NAME
from lecturepilot.tuebingen_adapter import TuebingenIntegrationUnavailable
from lecturepilot.university_models import ExternalCourseCandidate, UniversityLoginResult
from auth_helpers import pending_university_login


def test_tuebingen_login_returns_courses_without_echoing_password(monkeypatch) -> None:
    monkeypatch.delenv("LECTUREPILOT_DEMO_INCLUDE_CREATED_COURSES", raising=False)
    app = create_app()
    app.state.tuebingen_adapter = _FakeTuebingenAdapter()
    client = TestClient(app)

    response = client.post(
        "/auth/login",
        json={
            "username": "student01",
            "password": "very-secret-password",
        },
    )

    assert response.status_code == 200
    assert "very-secret-password" not in response.text
    assert "httponly" in response.headers["set-cookie"].lower()
    assert SESSION_COOKIE_NAME in response.cookies
    payload = response.json()
    assert payload.pop("access_token") is None
    csrf_token = payload.pop("csrf_token")
    assert len(csrf_token) >= 32
    assert payload == {
        "username": "student01",
        "display_name": None,
        "email": None,
        "term": "Sommer 2026",
        "tenant_id": "tenant-tuebingen",
        "account_type": "student",
        "university_role": None,
        "roles": ["student"],
        "courses": [],
        "university_courses": [],
        "university_course_sync_status": "loading",
        "university_course_source_statuses": {"alma": "loading", "ilias": "loading"},
    }
    current = client.get("/me").json()
    assert current["university_course_sync_status"] == "ready"
    assert current["university_course_source_statuses"] == {"alma": "ready", "ilias": "error"}
    assert current["university_courses"] == [
        {
            "source": "alma",
            "external_course_id": "unit:42",
            "term": "Sommer 2026",
            "title": "Machine Learning",
            "number": None,
            "organization": "Department of Computer Science",
            "instructor": None,
            "display_url": None,
        }
    ]


def test_tuebingen_login_reports_missing_wrapper_dependency() -> None:
    app = create_app()
    app.state.tuebingen_adapter = _UnavailableTuebingenAdapter()
    client = TestClient(app)

    response = client.post(
        "/auth/login",
        json={
            "username": "student01",
            "password": "secret",
        },
    )

    assert response.status_code == 503
    assert "tue-api-wrapper" in response.json()["detail"]


class _FakeTuebingenAdapter:
    def authenticate(self, *, username: str, password: str, term: str):
        assert password == "very-secret-password"
        return pending_university_login(
            UniversityLoginResult(
                username=username,
                term=term,
                courses=[
                    ExternalCourseCandidate(
                        source="alma",
                        external_course_id="unit:42",
                        title="Machine Learning",
                        organization="Department of Computer Science",
                        term=term,
                    )
                ],
                sources_checked={"alma"},
            ),
            preload_profile=False,
        )


class _UnavailableTuebingenAdapter:
    def authenticate(self, *, username: str, password: str, term: str):
        raise TuebingenIntegrationUnavailable("tue-api-wrapper is not installed.")
