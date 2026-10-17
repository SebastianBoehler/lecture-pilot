"""Apply one-time storage migrations before the API serves requests.

Each migration exposes ``migrate(storage_root, *, apply) -> dict`` and is idempotent. Applied ids
are recorded in ``.storage-migrations.json`` below the storage root, so later boots skip them.
The API runs pending migrations in its lifespan (one process, before serving). Operators can
inspect what would change with ``python -m lecturepilot.storage_migrations``.
"""

from __future__ import annotations

import argparse
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
import json
import logging
from pathlib import Path

from fastapi import FastAPI
from starlette.concurrency import run_in_threadpool

from lecturepilot.migrations_storage import (
    storage_migration_canvas_boilerplate,
    storage_migration_generic_reviews,
    storage_migration_learning_design_approval,
    storage_migration_lecture_source_alias,
    storage_migration_legacy_publications,
    storage_migration_legacy_workspaces,
    storage_migration_practice_design_schema,
    storage_migration_practice_exam_ppi,
)
from lecturepilot.canvas.canvas_workspace_config import default_workspace_root
from lecturepilot.core.durable_files import atomic_write_json


logger = logging.getLogger(__name__)

STATE_FILE = ".storage-migrations.json"
Migration = Callable[..., dict]

# Ordered; ids are permanent. Append new migrations, never rename or reorder applied ones.
MIGRATIONS: tuple[tuple[str, Migration], ...] = (
    ("2026-10-canvas-boilerplate", storage_migration_canvas_boilerplate.migrate),
    ("2026-10-legacy-workspaces", storage_migration_legacy_workspaces.migrate),
    # Draft approvals are reduced after designs reach schema 2.
    ("2026-10-practice-design-schema-2", storage_migration_practice_design_schema.migrate),
    ("2026-10-learning-design-approval", storage_migration_learning_design_approval.migrate),
    # Keeps revisions bound before lecture-local source revisions current.
    ("2026-10-lecture-source-alias", storage_migration_lecture_source_alias.migrate),
    # The strict practice-exam model no longer carries retired PPI pattern fields.
    ("2026-10-practice-exam-ppi", storage_migration_practice_exam_ppi.migrate),
    ("2026-10-generic-checkpoint-reviews", storage_migration_generic_reviews.migrate),
)


def applied_migration_ids(storage_root: Path) -> list[str]:
    path = storage_root / STATE_FILE
    if not path.is_file():
        return []
    return list(json.loads(path.read_text(encoding="utf-8")).get("applied", []))


def apply_pending(storage_root: Path) -> list[dict]:
    """Apply every migration not yet recorded; record each one right after it succeeds."""
    applied = applied_migration_ids(storage_root)
    reports = []
    for migration_id, migrate in MIGRATIONS:
        if migration_id in applied:
            continue
        report = migrate(storage_root, apply=True)
        applied.append(migration_id)
        storage_root.mkdir(parents=True, exist_ok=True)
        atomic_write_json(storage_root / STATE_FILE, {"applied": applied})
        logger.info("storage migration applied", extra={"migration": migration_id})
        reports.append({"id": migration_id, **report})
    legacy = storage_migration_legacy_publications.migrate(storage_root)
    if legacy.get("legacy_publications"):
        logger.warning(
            "legacy publications remain",
            extra={"count": len(legacy["legacy_publications"])},
        )
    return reports


@asynccontextmanager
async def migrate_storage_on_startup(app: FastAPI) -> AsyncIterator[None]:
    """FastAPI lifespan: finish pending migrations before the first request is served."""
    await run_in_threadpool(apply_pending, app.state.canvas_workspace.workspace_root)
    yield


def dry_run(storage_root: Path) -> dict:
    applied = set(applied_migration_ids(storage_root))
    return {
        "storage_root": str(storage_root),
        "pending": [
            {"id": migration_id, **migrate(storage_root, apply=False)}
            for migration_id, migrate in MIGRATIONS
            if migration_id not in applied
        ],
        "applied": sorted(applied),
        "legacy_publications": storage_migration_legacy_publications.migrate(storage_root),
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=default_workspace_root())
    parser.add_argument("--apply", action="store_true", help="apply pending migrations")
    args = parser.parse_args(argv)
    result = apply_pending(args.root) if args.apply else dry_run(args.root)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
