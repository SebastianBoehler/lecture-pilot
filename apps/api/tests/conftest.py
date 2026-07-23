from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text

from lecturepilot.database import _psycopg_url


@pytest.fixture(autouse=True)
def local_dev_auth_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LECTUREPILOT_ENV", "test")
    monkeypatch.setenv("LECTUREPILOT_AUTH_MODE", "dev")
    monkeypatch.setenv(
        "LECTUREPILOT_ALLOWED_MODELS",
        "openai/gpt-5.6-luna,gemini/gemini-3.1-flash-lite,gemini/test-model,"
        "openrouter/z-ai/glm-5.1,openrouter/openai/gpt-oss-120b:nitro",
    )
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return
    engine = create_engine(_psycopg_url(database_url))
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE usage_counters, audit_events, course_enrollments, "
                "course_external_refs, courses, external_course_observations, sessions, "
                "tenant_memberships, external_identities, users CASCADE"
            )
        )
    engine.dispose()
