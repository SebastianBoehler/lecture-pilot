from __future__ import annotations

import json
from pathlib import PurePosixPath

from lecturepilot.storage_layout import safe_id


def normalize_student_canvas_markdown(logical_path: str, content: str) -> str:
    if not logical_path.startswith("/lecture/canvas/student/"):
        return content
    if not logical_path.endswith(".md") or content.lstrip().startswith("---\n"):
        return content
    section_id = safe_id(PurePosixPath(logical_path).name)
    title = _title_from_markdown(content) or _title_from_id(section_id)
    body = _body_without_first_title(content).strip()
    return (
        "---\n"
        f"id: {json.dumps(section_id)}\n"
        f"title: {json.dumps(title)}\n"
        'source_ref: "student workspace"\n'
        "---\n\n"
        f"{body}\n"
    )


def student_canvas_section_id(logical_path: str, content: str) -> str | None:
    if not logical_path.startswith("/lecture/canvas/student/") or not logical_path.endswith(".md"):
        return None
    for line in content.splitlines():
        key, _, value = line.partition(":")
        if key.strip() == "id":
            return str(json.loads(value.strip()))
    return safe_id(PurePosixPath(logical_path).name)


def _title_from_markdown(content: str) -> str | None:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped.removeprefix("# ").strip()[:120] or None
    return None


def _body_without_first_title(content: str) -> str:
    lines = content.splitlines()
    for index, line in enumerate(lines):
        if line.strip().startswith("# "):
            return "\n".join([*lines[:index], *lines[index + 1 :]])
    return content


def _title_from_id(section_id: str) -> str:
    return section_id.replace("-", " ").removesuffix(" md").title()
