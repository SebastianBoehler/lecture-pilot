"""Provision explicit synthetic sessions only in a disposable local capacity DB."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

from lecturepilot.database import Database, DatabaseSettings
from lecturepilot.identity_repository import IdentityRepository
from lecturepilot.session_store import SessionStore
from lecturepilot.university_models import UniversityLoginResult
from lecturepilot.course_schedule_store import (
    read_course_workspace,
    overwrite_course_workspace,
)
from lecturepilot.models import CourseAccessPolicy


def validate_database(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme not in {"postgresql", "postgresql+psycopg"}:
        raise ValueError("Capacity fixture requires PostgreSQL.")
    if parsed.hostname not in {"127.0.0.1", "localhost", "lecturepilot-capacity-db"}:
        raise ValueError("Capacity fixture requires a local disposable database.")
    if parsed.path != "/lecturepilot_capacity_pytest":
        raise ValueError("Capacity fixture requires lecturepilot_capacity_pytest.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--users", type=int, default=40)
    parser.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.users <= 100:
        parser.error("users must be between 1 and 100")
    url = os.environ.get("DATABASE_URL", "")
    validate_database(url)
    output = args.output.resolve()
    output_root = Path(__file__).resolve().parents[1] / "output"
    if not output.is_relative_to(output_root) or "capacity" not in str(output):
        parser.error(
            "session output must be below an ignored output capacity directory"
        )
    if output.exists():
        parser.error("session output already exists; use a new filename")
    workspace = args.workspace.resolve()
    if not workspace.is_relative_to(output_root) or "capacity" not in str(workspace):
        parser.error("workspace must be an isolated capacity copy below output")
    course_root = workspace / "courses/tenant-tuebingen/martius-ml"
    course = read_course_workspace(course_root, "martius-ml")
    if course is None:
        parser.error("Copied prepared course workspace is required")
    # Synthetic accounts are not university enrollments. Only the private copied
    # fixture admits all authenticated members; published content remains unchanged.
    course.course.access_policy = CourseAccessPolicy.PLATFORM_AUTHENTICATED
    for lecture in course.lectures:
        if lecture.access_override:
            lecture.access_override.audience = CourseAccessPolicy.PLATFORM_AUTHENTICATED
    overwrite_course_workspace(course_root, course)
    database = Database(
        DatabaseSettings(
            url=url.replace("postgresql://", "postgresql+psycopg://"), required=True
        )
    )
    identities = IdentityRepository(database)
    sessions = SessionStore(database)
    tokens = []
    for index in range(args.users):
        account = identities.record_login(
            UniversityLoginResult(
                username=f"capacity-synthetic-{index:03d}",
                display_name=f"Synthetic capacity learner {index}",
                term="Sommer 2026",
                courses=[],
                sources_checked=set(),
            ),
            tenant_id="tenant-tuebingen",
        )
        tokens.append(sessions.create(account, ttl_minutes=120).token)
    output.parent.mkdir(parents=True, exist_ok=True)
    with os.fdopen(
        os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w"
    ) as handle:
        json.dump({"synthetic": True, "tokens": tokens}, handle)
    print(json.dumps({"synthetic_sessions_created": len(tokens)}))


if __name__ == "__main__":
    main()
