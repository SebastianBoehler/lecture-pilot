from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from lecturepilot.models import UserMemoryContext
from lecturepilot.storage_layout import StorageLayout


class UserMemoryStore:
    """File-backed learner memory for cross-course tutor personalization."""

    def __init__(self, layout: StorageLayout) -> None:
        self.layout = layout

    def read_context(self, user_id: str, course_id: str | None = None) -> UserMemoryContext:
        root = self.layout.user_root(user_id)
        memories = self.layout.user_memories_dir(user_id)
        root.mkdir(parents=True, exist_ok=True)
        memories.mkdir(parents=True, exist_ok=True)

        profile_path = root / "profile.json"
        preferences_path = memories / "preferences.json"
        global_path = memories / "global.md"
        global_trace_path = memories / "memory-trace.jsonl"
        course_path = None
        course_trace_path = None
        if course_id:
            course_memories = self.layout.user_course_memories_dir(user_id, course_id)
            course_memories.mkdir(parents=True, exist_ok=True)
            course_path = course_memories / "course.md"
            course_trace_path = course_memories / "memory-trace.jsonl"

        if not profile_path.exists():
            profile_path.write_text(
                json.dumps({"schema_version": 1, "user_key": self.layout.user_key(user_id)}, indent=2),
                encoding="utf-8",
            )
        if not preferences_path.exists():
            preferences_path.write_text("{}\n", encoding="utf-8")
        if not global_path.exists():
            global_path.write_text("", encoding="utf-8")
        if not global_trace_path.exists():
            global_trace_path.write_text("", encoding="utf-8")
        if course_path and not course_path.exists():
            course_path.write_text("", encoding="utf-8")
        if course_trace_path and not course_trace_path.exists():
            course_trace_path.write_text("", encoding="utf-8")

        return UserMemoryContext(
            global_notes=global_path.read_text(encoding="utf-8")[:4000],
            course_notes=(course_path.read_text(encoding="utf-8")[:4000] if course_path else ""),
            preferences=_read_preferences(preferences_path),
        )

    def remember(
        self,
        *,
        user_id: str,
        course_id: str,
        lecture_id: str,
        note: str,
        scope: str = "global",
        preference_key: str | None = None,
        preference_value: str | None = None,
    ) -> dict[str, Any]:
        scope = scope.strip().lower()
        if scope not in {"global", "course"}:
            raise ValueError("Memory scope must be global or course.")

        self.read_context(user_id, course_id)
        memories = (
            self.layout.user_course_memories_dir(user_id, course_id)
            if scope == "course"
            else self.layout.user_memories_dir(user_id)
        )
        note = note.strip()
        if note:
            notes_path = memories / ("course.md" if scope == "course" else "global.md")
            current = notes_path.read_text(encoding="utf-8") if notes_path.exists() else ""
            notes_path.write_text((current.rstrip() + f"\n- {note}\n").lstrip(), encoding="utf-8")
        if preference_key:
            pref_path = self.layout.user_memories_dir(user_id) / "preferences.json"
            prefs = _read_preferences(pref_path)
            prefs[preference_key] = preference_value or ""
            pref_path.write_text(json.dumps(prefs, indent=2), encoding="utf-8")
        self._append_trace(memories, scope, course_id, lecture_id, note, preference_key, preference_value)
        return {"memory": "updated", "scope": scope}

    def _append_trace(
        self,
        memories,
        scope: str,
        course_id: str,
        lecture_id: str,
        note: str,
        preference_key: str | None,
        preference_value: str | None,
    ) -> None:
        trace = {
            "schema_version": 1,
            "created_at": datetime.now(UTC).isoformat(),
            "scope": scope,
            "course_id": course_id if scope == "course" else None,
            "lecture_id": lecture_id,
            "tool": "remember",
            "note": note,
            "preference_key": preference_key,
            "preference_value": preference_value,
        }
        trace_path = memories / "memory-trace.jsonl"
        current = trace_path.read_text(encoding="utf-8") if trace_path.exists() else ""
        trace_path.write_text(f"{current}{json.dumps(trace, sort_keys=True)}\n", encoding="utf-8")


def _read_preferences(path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8") or "{}")
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}
