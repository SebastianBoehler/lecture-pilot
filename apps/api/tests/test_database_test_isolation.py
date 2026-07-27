from __future__ import annotations

import os

from sqlalchemy.engine import make_url

from lecturepilot.runtime_env import load_project_env


load_project_env()


def test_api_suite_uses_dedicated_pytest_database() -> None:
    database_url = os.environ["DATABASE_URL"]

    assert make_url(database_url).database.endswith("_pytest")
