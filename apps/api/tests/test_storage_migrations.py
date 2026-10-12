from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from lecturepilot import storage_migrations
from lecturepilot.storage_migrations import (
    STATE_FILE,
    applied_migration_ids,
    apply_pending,
    dry_run,
    migrate_storage_on_startup,
)


def _legacy_learner_file(root: Path) -> Path:
    path = root / "workspaces" / "students" / "abc123" / "notes.md"
    path.parent.mkdir(parents=True)
    path.write_text("orphaned", encoding="utf-8")
    return path


def test_dry_run_reports_pending_migrations_without_changing_storage(tmp_path: Path) -> None:
    legacy = _legacy_learner_file(tmp_path)

    report = dry_run(tmp_path)

    assert [item["id"] for item in report["pending"]] == [
        migration_id for migration_id, _ in storage_migrations.MIGRATIONS
    ]
    assert legacy.exists()
    assert not (tmp_path / STATE_FILE).exists()


def test_apply_pending_runs_each_migration_once_and_records_it(tmp_path: Path) -> None:
    legacy = _legacy_learner_file(tmp_path)

    first = apply_pending(tmp_path)
    second = apply_pending(tmp_path)

    assert not legacy.exists()
    assert [item["id"] for item in first] == applied_migration_ids(tmp_path)
    assert second == []
    assert dry_run(tmp_path)["pending"] == []


def test_apply_pending_skips_recorded_migrations(tmp_path: Path, monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        storage_migrations,
        "MIGRATIONS",
        (
            ("done", lambda root, *, apply: calls.append("done") or {}),
            ("new", lambda root, *, apply: calls.append("new") or {"applied": apply}),
        ),
    )
    (tmp_path / STATE_FILE).write_text(json.dumps({"applied": ["done"]}), encoding="utf-8")

    reports = apply_pending(tmp_path)

    assert calls == ["new"]
    assert reports == [{"id": "new", "applied": True}]
    assert applied_migration_ids(tmp_path) == ["done", "new"]


def test_lifespan_applies_pending_migrations_before_serving(tmp_path: Path) -> None:
    legacy = _legacy_learner_file(tmp_path)
    app = FastAPI(lifespan=migrate_storage_on_startup)
    app.state.canvas_workspace = SimpleNamespace(workspace_root=tmp_path)

    with TestClient(app):
        assert not legacy.exists()

    assert applied_migration_ids(tmp_path)
