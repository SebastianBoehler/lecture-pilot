"""Remove learner data that no reader can reach any more.

Learner writes moved from ``workspaces/students/<user-key>/...`` to ``users/<user-key>/...``
and compiled ``canvas.json`` caches were replaced by the Markdown canvas. Nothing reads either,
so the data is orphaned (and would otherwise survive learner resets and course deletion).
Run it while the API is stopped. It is a dry run unless ``apply=True`` and is idempotent.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
import shutil


LEGACY_LEARNER_ROOT = Path("workspaces") / "students"


def migrate(storage_root: Path, *, apply: bool = False) -> dict:
    legacy_root = storage_root / LEGACY_LEARNER_ROOT
    legacy_exists = legacy_root.is_dir()
    stale = sorted(_stale_canvas_json(storage_root))
    report = {
        "migration": "legacy_workspaces",
        "applied": apply,
        "legacy_root": LEGACY_LEARNER_ROOT.as_posix() if legacy_exists else None,
        "legacy_root_files": _count_files(legacy_root) if legacy_exists else 0,
        "stale_canvas_json": [str(path.relative_to(storage_root)) for path in stale],
    }
    if not apply:
        return report
    if legacy_exists:
        shutil.rmtree(legacy_root)
        _remove_if_empty(legacy_root.parent)
    for path in stale:
        path.unlink(missing_ok=True)
    return report


def _stale_canvas_json(storage_root: Path) -> Iterator[Path]:
    for users_root in (storage_root / "users", storage_root / "previews" / "professors"):
        for path in users_root.glob("*/courses/*/lectures/*/canvas.json"):
            if path.is_file() and not path.is_symlink():
                yield path


def _count_files(root: Path) -> int:
    return sum(1 for path in root.rglob("*") if path.is_file())


def _remove_if_empty(path: Path) -> None:
    if path.is_dir() and not any(path.iterdir()):
        path.rmdir()
