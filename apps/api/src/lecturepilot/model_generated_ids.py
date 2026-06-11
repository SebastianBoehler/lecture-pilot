from __future__ import annotations

import re
from datetime import UTC, datetime


def student_section_id(value: str) -> str:
    safe = safe_generated_id(value)
    if safe.startswith("student-"):
        return safe
    suffix = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    return f"student-{safe[:80]}-{suffix}"


def safe_generated_id(value: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.lower()).strip("-")
    return (safe or "generated-note")[:120]


def trim_generated_text(value: str, limit: int) -> str:
    cleaned = " ".join(value.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."
