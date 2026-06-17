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
    content = _normalize_model_block_lines(content)
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


def _normalize_model_block_lines(content: str) -> str:
    lines = content.splitlines()
    schema_quiz = _schema_quiz_from_lines(lines)
    if schema_quiz:
        title = _line_value(lines, "title")
        if title and not _title_from_markdown(content):
            return "\n".join([f"# {title}", "", *schema_quiz]).strip() + "\n"
        return "\n".join(schema_quiz)
    normalized: list[str] = []
    title = None
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.strip() == "quiz:":
            block, index = _quiz_block_from_yamlish_lines(lines, index)
            normalized.extend(block)
            continue
        fields = _model_fields(line)
        block_type = fields.get("type")
        if fields.get("section_id") and fields.get("title"):
            title = fields["title"]
            index += 1
            continue
        if block_type in {"checkpoint", "quiz"} and fields.get("text"):
            normalized.extend(_rich_block_from_fields(fields, block_type))
            index += 1
            continue
        normalized.append(line)
        index += 1
    if title and not _title_from_markdown(content):
        return "\n".join([f"# {title}", "", *normalized]).strip() + "\n"
    return "\n".join(normalized)


def _model_fields(line: str) -> dict[str, str]:
    if "=" not in line or ";" not in line:
        return {}
    fields: dict[str, str] = {}
    for part in line.split(";"):
        key, separator, value = part.partition("=")
        if separator:
            fields[key.strip()] = value.strip()
    return fields


def _rich_block_from_fields(fields: dict[str, str], block_type: str) -> list[str]:
    block_id = safe_id(fields.get("span_id") or fields.get("id") or block_type)
    lines = [f'<!-- block id="{block_id}" type="{block_type}" -->', f":::{block_type}", fields["text"]]
    if block_type == "quiz":
        for item in _items_from_model_field(fields.get("items", "")):
            lines.append(f"- {item}")
    lines.append(":::")
    return lines


def _items_from_model_field(value: str) -> list[str]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    return [str(item) for item in parsed] if isinstance(parsed, list) else []


def _quiz_block_from_yamlish_lines(lines: list[str], start: int) -> tuple[list[str], int]:
    question = ""
    items: list[tuple[str, bool]] = []
    current_text = ""
    current_correct = False
    in_items = False
    index = start + 1
    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped:
            index += 1
            continue
        if stripped == "items:":
            in_items = True
            index += 1
            continue
        if stripped.startswith("text:") and not in_items:
            question = _unquote(stripped.partition(":")[2].strip())
        elif stripped.startswith("- "):
            if current_text:
                items.append((current_text, current_correct))
            current_text = ""
            current_correct = False
        elif stripped.startswith("text:"):
            current_text = _unquote(stripped.partition(":")[2].strip())
        elif stripped.startswith("correct:"):
            current_correct = stripped.partition(":")[2].strip().lower() == "true"
        elif stripped.endswith(":"):
            break
        index += 1
    if current_text:
        items.append((current_text, current_correct))
    block = ['<!-- block id="generated-quiz" type="quiz" -->', ":::quiz", question]
    for item, correct in items:
        block.append(f"- {'[x] ' if correct else ''}{item}")
    block.append(":::")
    return block, index


def _schema_quiz_from_lines(lines: list[str]) -> list[str] | None:
    stripped_lines = [line.strip() for line in lines]
    looks_like_quiz = (
        "type=quiz" in stripped_lines
        or "--- quiz" in stripped_lines
        or ("items:" in stripped_lines and any(line.startswith("correct") for line in stripped_lines))
    )
    if not looks_like_quiz:
        return None
    block_id = safe_id(_line_value(lines, "span_id") or "generated-quiz")
    question = _line_value(lines, "text")
    items = _schema_items_from_lines(lines)
    block = [f'<!-- block id="{block_id}" type="quiz" -->', ":::quiz", question]
    for item, correct in items:
        block.append(f"- {'[x] ' if correct else ''}{item}")
    block.append(":::")
    return block


def _schema_items_from_lines(lines: list[str]) -> list[tuple[str, bool]]:
    items: list[tuple[str, bool]] = []
    in_items = False
    current_text = ""
    current_correct = False
    for line in lines:
        stripped = line.strip()
        if stripped == "items:":
            in_items = True
            continue
        if not in_items:
            continue
        if stripped.startswith("id="):
            if current_text:
                items.append((current_text, current_correct))
            current_text = ""
            current_correct = False
        elif stripped.startswith("- id:"):
            if current_text:
                items.append((current_text, current_correct))
            current_text = ""
            current_correct = False
        elif stripped.startswith("text=") or stripped.startswith("text:"):
            current_text = _field_value(stripped)
        elif stripped.startswith("correct=") or stripped.startswith("correct:"):
            current_correct = _field_value(stripped).lower() == "true"
        elif not stripped.startswith("---") and not _is_schema_assignment(stripped):
            if current_text:
                items.append((current_text, current_correct))
            current_text = stripped
            current_correct = False
    if current_text:
        items.append((current_text, current_correct))
    return items


def _line_value(lines: list[str], key: str) -> str:
    equals_prefix = f"{key}="
    colon_prefix = f"{key}:"
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(equals_prefix) or stripped.startswith(colon_prefix):
            return _field_value(stripped)
    return ""


def _is_schema_assignment(line: str) -> bool:
    key = line.partition("=")[0].partition(":")[0].strip()
    return key in {"id", "section_id", "span_id", "title", "type", "text", "correct"}


def _field_value(line: str) -> str:
    _, separator, value = line.partition("=")
    if not separator:
        _, _, value = line.partition(":")
    return _unquote(value.strip())


def _unquote(value: str) -> str:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return value.strip("\"'")
    return str(parsed)


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
