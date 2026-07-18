from __future__ import annotations

import json
import re

from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError


def parse_model_json(content: str | None) -> dict:
    if not content:
        raise CanvasGenerationRepairableError("Course planner returned an empty response.")
    cleaned = _strip_code_fence(content.strip())
    candidates = [cleaned]
    candidates.extend(_escape_invalid_json_backslashes(candidate) for candidate in list(candidates))
    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
        raise CanvasGenerationRepairableError("Course planner JSON must be an object.")
    raise CanvasGenerationRepairableError("Course planner did not return valid JSON.")


def _escape_invalid_json_backslashes(content: str) -> str:
    return re.sub(r'\\(?!["\\/bfnrtu])', r"\\\\", content)


def _strip_code_fence(content: str) -> str:
    if not content.startswith("```"):
        return content
    lines = content.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()
