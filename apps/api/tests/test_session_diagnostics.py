from __future__ import annotations

import json
import logging

from fastapi.testclient import TestClient

from lecturepilot.app import create_app
from lecturepilot.logging_observability import LoggingObservability
from lecturepilot.metadata_events import LOGGER_NAME
from lecturepilot.session_auth import SESSION_COOKIE_NAME
from lecturepilot.session_store import SessionStoreError
from lecturepilot.tuebingen_adapter import TuebingenIntegrationUnavailable
from lecturepilot.university_models import ExternalCourseCandidate, UniversityLoginResult
from auth_helpers import pending_university_login


class _ExpiredSessionStore:
    def authenticate(self, _token: str):
        raise SessionStoreError(
            "Session has expired.",
            reason="expired",
            duration_ms=3_600_000,
        )


class _UniversityAdapter:
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
                        term=term,
                    )
                ],
                sources_checked={"alma"},
            )
        )


class _UnavailableUniversityAdapter:
    def authenticate(self, *, username: str, password: str, term: str):
        raise TuebingenIntegrationUnavailable("tue-api-wrapper is not installed.")


def test_expired_session_logs_reason_and_duration_without_token(caplog) -> None:
    app = create_app()
    app.state.session_store = _ExpiredSessionStore()
    client = TestClient(app)
    client.cookies.set(SESSION_COOKIE_NAME, "private-session-token")

    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        response = client.get("/me")

    assert response.status_code == 401
    events = [json.loads(record.message) for record in caplog.records]
    rejected = next(event for event in events if event["event"] == "auth.session_rejected")
    assert rejected["reason"] == "expired"
    assert rejected["duration_ms"] == 3_600_000
    assert "private-session-token" not in "\n".join(record.message for record in caplog.records)


def test_login_and_course_sync_log_safe_outcomes(caplog) -> None:
    app = create_app()
    app.state.observability = LoggingObservability()
    app.state.tuebingen_adapter = _UniversityAdapter()

    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        response = TestClient(app).post(
            "/auth/login",
            json={"username": "student01", "password": "very-secret-password"},
        )

    assert response.status_code == 200
    events = [json.loads(record.message) for record in caplog.records]
    finished = {
        event["span"]: event for event in events if event["event"] == "observability.span_finished"
    }
    assert finished["lecturepilot.auth_login"]["outcome"] == "success"
    assert finished["lecturepilot.auth_login"]["account_type"] == "student"
    assert finished["lecturepilot.university_course_sync"]["course_count"] == 1
    assert finished["lecturepilot.university_course_sync"]["source_count"] == 1
    assert "student01" not in "\n".join(record.message for record in caplog.records)


def test_unavailable_login_integration_logs_safe_failure_reason(caplog) -> None:
    app = create_app()
    app.state.observability = LoggingObservability()
    app.state.tuebingen_adapter = _UnavailableUniversityAdapter()

    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        response = TestClient(app).post(
            "/auth/login",
            json={"username": "student01", "password": "secret"},
        )

    assert response.status_code == 503
    events = [json.loads(record.message) for record in caplog.records]
    event = next(
        event
        for event in events
        if event["event"] == "observability.span_finished"
        and event["span"] == "lecturepilot.auth_login"
    )
    assert event["status"] == "error"
    assert event["reason"] == "integration_unavailable"
    assert "student01" not in "\n".join(record.message for record in caplog.records)
