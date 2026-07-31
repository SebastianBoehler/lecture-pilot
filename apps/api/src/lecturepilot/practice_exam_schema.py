from __future__ import annotations

from typing import Any


def practice_exam_response_format(
    *,
    question_count: int,
    authoritative_source_ids: set[str],
    selected_ppi_source_ids: set[str],
) -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "lecturepilot_practice_exam",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "title": {"type": "string"},
                    "instructions": {"type": "array", "items": {"type": "string"}},
                    "questions": {
                        "type": "array",
                        "minItems": question_count,
                        "maxItems": question_count,
                        "items": _question_schema(
                            authoritative_source_ids=authoritative_source_ids,
                            selected_ppi_source_ids=selected_ppi_source_ids,
                        ),
                    },
                },
                "required": ["title", "instructions", "questions"],
            },
        },
    }


def _question_schema(
    *, authoritative_source_ids: set[str], selected_ppi_source_ids: set[str]
) -> dict[str, Any]:
    properties: dict[str, Any] = {
        "id": {"type": "string"},
        "kind": {"type": "string", "enum": ["multiple_choice", "open_ended"]},
        "prompt": {"type": "string"},
        "points": {"type": "integer", "minimum": 1, "maximum": 50},
        "difficulty": {
            "type": "string",
            "enum": ["introductory", "standard", "advanced"],
        },
        "options": {"type": "array", "items": {"type": "string"}, "maxItems": 6},
        "answer_index": {"type": ["integer", "null"], "minimum": 0, "maximum": 5},
        "rubric": {"type": "array", "items": {"type": "string"}, "maxItems": 8},
        "source_ids": {
            "type": "array",
            "items": {"type": "string", "enum": sorted(authoritative_source_ids)},
            "minItems": 1,
            "maxItems": 8,
        },
        "ppi_pattern_ids": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 0,
        },
    }
    if selected_ppi_source_ids:
        properties["ppi_pattern_ids"] = {
            "type": "array",
            "items": {"type": "string", "enum": sorted(selected_ppi_source_ids)},
            "maxItems": 8,
        }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": list(properties),
    }
