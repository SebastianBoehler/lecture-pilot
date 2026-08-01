from __future__ import annotations

import os

import pytest
from sqlalchemy.engine import make_url

from lecturepilot.runtime_env import load_project_env


load_project_env()


def test_api_suite_uses_dedicated_pytest_database() -> None:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        pytest.skip("PostgreSQL test database is not configured.")

    assert make_url(database_url).database.endswith("_pytest")
