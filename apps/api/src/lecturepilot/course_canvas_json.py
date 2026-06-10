from __future__ import annotations

import json
import re

from lecturepilot.providers import ProviderConfigurationError


def parse_model_json(content: str | None) -> dict:
    if not content:
        raise ProviderConfigurationError("Course planner returned an empty response.")
    cleaned = _strip_code_fence(content.strip())
    candidates = [cleaned]
    if extracted := _extract_first_json_object(cleaned):
        candidates.append(extracted)
    candidates.extend(_escape_invalid_json_backslashes(candidate) for candidate in list(candidates))
    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
        raise ProviderConfigurationError("Course planner JSON must be an object.")
    raise ProviderConfigurationError("Course planner did not return valid JSON.")


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


def _extract_first_json_object(content: str) -> str | None:
    start = content.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escaped = False
    for index, char in enumerate(content[start:], start=start):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = in_string
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return content[start : index + 1]
    return None
