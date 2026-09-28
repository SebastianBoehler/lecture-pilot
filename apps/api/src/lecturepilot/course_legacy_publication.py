"""Identify obsolete publication metadata without accepting it as published content."""

import json
from pathlib import Path

from lecturepilot.canvas_snapshot import locked_canvas_access


def is_legacy_publication(published_dir: Path) -> bool:
    with locked_canvas_access(published_dir):
        path = published_dir / "publication.json"
        if not path.exists():
            return False
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return False
    return (
        isinstance(payload, dict)
        and type(payload.get("schema_version")) is int
        and payload["schema_version"] == 1
        and {"source_draft_path", "published_path"} <= payload.keys()
        and not {"source_revision", "draft_digest", "learning_map_revision"} & payload.keys()
    )
