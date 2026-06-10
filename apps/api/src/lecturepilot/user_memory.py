from __future__ import annotations

import json
from typing import Any

from lecturepilot.models import UserMemoryContext
from lecturepilot.storage_layout import StorageLayout


class UserMemoryStore:
    """File-backed learner memory for cross-course tutor personalization."""

    def __init__(self, layout: StorageLayout) -> None:
        self.layout = layout

    def read_context(self, user_id: str) -> UserMemoryContext:
        root = self.layout.user_root(user_id)
        memories = self.layout.user_memories_dir(user_id)
        root.mkdir(parents=True, exist_ok=True)
        memories.mkdir(parents=True, exist_ok=True)

        profile_path = root / "profile.json"
        preferences_path = memories / "preferences.json"
        global_path = memories / "global.md"

        if not profile_path.exists():
            profile_path.write_text(
                json.dumps({"schema_version": 1, "user_key": self.layout.user_key(user_id)}, indent=2),
                encoding="utf-8",
            )
        if not preferences_path.exists():
            preferences_path.write_text("{}\n", encoding="utf-8")
        if not global_path.exists():
            global_path.write_text("", encoding="utf-8")

        return UserMemoryContext(
            global_notes=global_path.read_text(encoding="utf-8")[:4000],
            preferences=_read_preferences(preferences_path),
        )


def _read_preferences(path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8") or "{}")
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}
