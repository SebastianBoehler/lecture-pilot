from __future__ import annotations

import json
from pathlib import PurePosixPath
from pathlib import Path

from lecturepilot.storage_layout import safe_id


def prepare_student_canvas_write(logical_path: str, path: Path, content: str) -> tuple[Path, str, str | None]:
    content = normalize_student_canvas_markdown(logical_path, content)
    section_id = student_canvas_section_id(logical_path, content)
    if is_student_markdown_path(logical_path):
        path = append_ordered_student_path(path, section_id)
    return path, content, section_id


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


def append_ordered_student_path(path: Path, section_id: str | None) -> Path:
    if path.exists() or _has_order_prefix(path.name):
        return path
    existing = _path_for_section_id(path.parent, section_id)
    if existing is not None:
        return existing
    return path.with_name(f"{_next_order_prefix(path.parent):02d}-{path.name}")


def is_student_markdown_path(logical_path: str) -> bool:
    return logical_path.startswith("/lecture/canvas/student/") and logical_path.endswith(".md")


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


def _path_for_section_id(directory: Path, section_id: str | None) -> Path | None:
    if not section_id or not directory.exists():
        return None
    marker = f'id: {json.dumps(section_id)}'
    for candidate in sorted(directory.glob("*.md")):
        if marker in candidate.read_text(encoding="utf-8", errors="ignore").splitlines()[:6]:
            return candidate
    return None


def _next_order_prefix(directory: Path) -> int:
    values = []
    if directory.exists():
        for candidate in directory.glob("*.md"):
            prefix = candidate.name.split("-", 1)[0]
            if prefix.isdigit():
                values.append(int(prefix))
    return max(values, default=89) + 1


def _has_order_prefix(filename: str) -> bool:
    prefix = filename.split("-", 1)[0]
    return prefix.isdigit()
