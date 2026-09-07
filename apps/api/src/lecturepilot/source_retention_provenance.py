"""Keep teaching provenance stable across deletion of excluded, unused files."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

from lecturepilot.durable_files import atomic_write_json


def retention_provenance_path(course_root: Path) -> Path:
    return course_root / "builder" / "source-retention-provenance.json"


def retained_provenance(course_root: Path, current: str) -> str:
    path = retention_provenance_path(course_root)
    if not path.exists():
        return current
    receipt = json.loads(path.read_text())
    if receipt["remaining_digest"] != sha256(current.encode()).hexdigest():
        return current
    return receipt["teaching_provenance"]


def record_retention_provenance(course_root: Path, *, previous: str, remaining: str) -> None:
    atomic_write_json(
        retention_provenance_path(course_root),
        {
            "remaining_digest": sha256(remaining.encode()).hexdigest(),
            "teaching_provenance": previous,
        },
    )
