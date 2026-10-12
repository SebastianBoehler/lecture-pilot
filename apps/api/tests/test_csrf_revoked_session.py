from __future__ import annotations

import os
from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient
import pytest

from security_db_helpers import candidate, login, mutation_headers
from test_database_security import _app

requires_database = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"), reason="PostgreSQL test database is required"
)
ROUTE = "/me/course-support-requests"
COURSE = {"source": "alma", "external_course_id": "title:secure", "term": "Sommer 2026"}


def _client(tmp_path: Path) -> tuple[TestClient, dict]:
    app = _app(tmp_path, {"student-a": [candidate("alma", "title:secure")]})
    client = TestClient(app, base_url="http://localhost:8000")
    return client, login(client, "student-a")


@requires_database
def test_mutation_with_a_revoked_session_is_unauthenticated(tmp_path: Path) -> None:
    client, session = _client(tmp_path)
    store = client.app.state.session_store
    store.revoke_user(UUID(client.get("/me").json()["user_id"]))

    response = client.put(ROUTE, headers=mutation_headers(session), json=COURSE)

    # The client must learn that the session ended, so it can ask the user to sign in again.
    assert response.status_code == 401, response.text


@requires_database
def test_wrong_csrf_token_on_a_live_session_stays_forbidden(tmp_path: Path) -> None:
    client, session = _client(tmp_path)
    headers = {**mutation_headers(session), "X-CSRF-Token": "not-the-token"}

    response = client.put(ROUTE, headers=headers, json=COURSE)

    assert response.status_code == 403, response.text
