from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from dotenv import dotenv_values

from lecturepilot.database import Database, _psycopg_url
from lecturepilot.runtime_env import _nearest_local_env

# Tests never inherit local provider keys or service URLs; only the dedicated test DB.
os.environ["LECTUREPILOT_ENV"] = "test"
_LOCAL_ENV = _nearest_local_env(Path(__file__).resolve())
_TEST_DATABASE_URL = (
    os.getenv("LECTUREPILOT_TEST_DATABASE_URL")
    or (dotenv_values(_LOCAL_ENV).get("LECTUREPILOT_TEST_DATABASE_URL") if _LOCAL_ENV else "")
    or ""
).strip()
if _TEST_DATABASE_URL and not (make_url(_TEST_DATABASE_URL).database or "").endswith("_pytest"):
    raise RuntimeError("LECTUREPILOT_TEST_DATABASE_URL must name a dedicated *_pytest database.")
if _TEST_DATABASE_URL:
    os.environ["DATABASE_URL"] = _TEST_DATABASE_URL
else:
    os.environ.pop("DATABASE_URL", None)


@pytest.fixture(autouse=True)
def local_dev_auth_defaults(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Apps built without an explicit root (and their startup migrations) never touch real data.
    monkeypatch.setenv("LECTUREPILOT_WORKSPACE_ROOT", str(tmp_path / "default-workspace"))
    monkeypatch.setenv("LECTUREPILOT_ENV", "test")
    monkeypatch.setenv("LECTUREPILOT_AUTH_MODE", "dev")
    monkeypatch.setenv(
        "LECTUREPILOT_ALLOWED_MODELS",
        "openai/gpt-5.6-luna,gemini/gemini-3.1-flash-lite,gemini/test-model,"
        "openrouter/z-ai/glm-5.1,openrouter/openai/gpt-oss-120b:nitro",
    )
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        return
    original_session = Database.session
    cleaned = False

    @contextmanager
    def isolated_session(database: Database) -> Iterator[Session]:
        nonlocal cleaned
        if not cleaned:
            _truncate_test_database(database_url)
            cleaned = True
        with original_session(database) as session:
            yield session

    monkeypatch.setattr(Database, "session", isolated_session)


def _truncate_test_database(database_url: str) -> None:
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
