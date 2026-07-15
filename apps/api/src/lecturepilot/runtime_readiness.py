from __future__ import annotations

from dataclasses import dataclass
import json
import os
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from lecturepilot.database import Database


COMPILER_HEALTH_TIMEOUT_SECONDS = 2


@dataclass(frozen=True)
class ReadinessResult:
    ready: bool
    checks: dict[str, str]

    @property
    def failed_checks(self) -> list[str]:
        return [name for name, status in self.checks.items() if status != "ok"]


class RuntimeReadiness:
    def __init__(self, database: Database) -> None:
        self.database = database

    def check(self) -> ReadinessResult:
        checks = {
            "database": _database_status(self.database),
            "latex_compiler": _compiler_status(),
        }
        return ReadinessResult(ready=all(value == "ok" for value in checks.values()), checks=checks)


def _database_status(database: Database) -> str:
    try:
        database.ping()
    except Exception:
        return "error"
    return "ok"


def _compiler_status() -> str:
    configured = os.getenv("LECTUREPILOT_LATEX_COMPILER_URL", "").strip()
    try:
        endpoint = _health_endpoint(configured)
        request = Request(endpoint, headers={"Accept": "application/json"})
        with urlopen(request, timeout=COMPILER_HEALTH_TIMEOUT_SECONDS) as response:
            payload = response.read(1025)
            if response.status != 200 or len(payload) > 1024:
                return "error"
        parsed = json.loads(payload)
    except Exception:
        return "error"
    return "ok" if parsed == {"status": "ok"} else "error"


def _health_endpoint(configured: str) -> str:
    parsed = urlsplit(configured)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Invalid compiler service URL.")
    return f"{configured.rstrip('/')}/health"
