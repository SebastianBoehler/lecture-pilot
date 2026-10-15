from __future__ import annotations

import json
import logging

from fastapi.testclient import TestClient

from lecturepilot.app import create_app
from lecturepilot.core.metadata_events import LOGGER_NAME
from lecturepilot.identity.session_auth import SESSION_COOKIE_NAME
from lecturepilot.identity.session_store import SessionStoreError


class _ExpiredSessionStore:
    def authenticate(
        self,
        _token: str,
        *,
        ttl_minutes: int | None = None,
        max_lifetime_minutes: int | None = None,
    ):
        del ttl_minutes, max_lifetime_minutes
        raise SessionStoreError(
            "Session has expired.",
            reason="expired",
            duration_ms=3_600_000,
        )


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
