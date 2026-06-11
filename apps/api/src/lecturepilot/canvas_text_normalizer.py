from __future__ import annotations

import ast
import re
from typing import Any


def clean_canvas_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        return _clean_mapping(value)
    if isinstance(value, list):
        return "\n".join(item for item in clean_canvas_items(value) if item)
    text = str(value).strip()
    parsed = _parse_structured_text(text)
    if parsed is not None:
        return clean_canvas_text(parsed)
    return _strip_markdown_artifacts(text)


def clean_canvas_items(values: list[Any]) -> list[str]:
    return [item for value in values if (item := clean_canvas_text(value))]


def _clean_mapping(value: dict) -> str:
    for key in ("content", "text", "summary", "paragraph"):
        if key in value:
            return clean_canvas_text(value[key])
    if isinstance(value.get("items"), list):
        return clean_canvas_text(value["items"])
    return ""


def _parse_structured_text(text: str) -> Any | None:
    if not text.startswith(("{", "[")):
        return None
    if not any(marker in text for marker in ("'type'", '"type"', "'content'", '"content"')):
        return None
    try:
        return ast.literal_eval(text)
    except (SyntaxError, ValueError):
        return None


def _strip_markdown_artifacts(text: str) -> str:
    text = re.sub(r"\\n(?=\s|[*-])", "\n", text)
    lines = [_strip_line(line) for line in text.splitlines()]
    return "\n".join(line for line in lines if line).strip()


def _strip_line(line: str) -> str:
    line = line.strip()
    while line.startswith(">"):
        line = line[1:].strip()
    return re.sub(r"^#{1,6}\s+", "", line).strip()
