from __future__ import annotations

from typing import Any

from lecturepilot.component_response_schema import component_data_schema


_BLOCK_TYPES = [
    "paragraph",
    "list",
    "asset",
    "callout",
    "math",
    "video",
    "checkpoint",
    "table",
]
_REQUIRED_BLOCK_FIELDS = [
    "id",
    "type",
    "text",
    "items",
    "asset_path",
    "asset_url",
    "caption",
    "answer_index",
    "component_id",
    "component_type",
    "component_ref",
    "component_version",
    "option_ids",
    "component_data",
]


def course_canvas_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "title": {"type": "string"},
            "sections": {"type": "array", "items": _section_schema()},
        },
        "required": ["title", "sections"],
    }


def _section_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "id": {"type": "string"},
            "title": {"type": "string"},
            "source_ref": {"type": ["string", "null"]},
            "blocks": {"type": "array", "items": _course_block_schema()},
        },
        "required": ["id", "title", "source_ref", "blocks"],
    }


def _course_block_schema() -> dict[str, Any]:
    return {
        "anyOf": [
            _ordinary_block_schema(),
            _quiz_schema(),
            _single_choice_schema(),
            _data_component_schema("interactive_chart"),
            _data_component_schema("process_explorer"),
            _data_component_schema("visual_artifact"),
        ]
    }


def _ordinary_block_schema() -> dict[str, Any]:
    properties = _common_properties()
    properties.update(
        {
            "type": {"type": "string", "enum": _BLOCK_TYPES},
            "component_id": {"type": "null"},
            "component_type": {"type": "null"},
            "component_ref": {"type": "null"},
            "component_version": {"type": "null"},
            "component_data": {"type": "null"},
        }
    )
    return _strict_block(properties)


def _quiz_schema() -> dict[str, Any]:
    properties = _common_properties()
    properties.update(
        {
            "type": {"type": "string", "const": "quiz"},
            "items": {"type": "array", "items": {"type": "string"}, "minItems": 2},
            "answer_index": {"type": "integer", "minimum": 0, "maximum": 25},
            "component_id": {"type": "null"},
            "component_type": {"type": "null"},
            "component_ref": {"type": "null"},
            "component_version": {"type": "null"},
            "component_data": {"type": "null"},
        }
    )
    return _strict_block(properties)


def _single_choice_schema() -> dict[str, Any]:
    properties = _component_properties("single_choice_quiz")
    properties.update(
        {
            "items": {"type": "array", "items": {"type": "string"}, "minItems": 2},
            "option_ids": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 2,
            },
            "answer_index": {"type": "integer", "minimum": 0, "maximum": 25},
            "component_data": {"type": "null"},
        }
    )
    return _strict_block(properties)


def _data_component_schema(component_type: str) -> dict[str, Any]:
    properties = _component_properties(component_type)
    properties["component_data"] = component_data_schema()
    return _strict_block(properties)


def _component_properties(component_type: str) -> dict[str, Any]:
    properties = _common_properties()
    properties.update(
        {
            "type": {"type": "string", "const": "component"},
            "component_id": {"type": "string"},
            "component_type": {"type": "string", "const": component_type},
            "component_version": {"type": "integer", "minimum": 1},
        }
    )
    return properties


def _common_properties() -> dict[str, Any]:
    return {
        "id": {"type": "string"},
        "text": {"type": ["string", "null"]},
        "items": {"type": "array", "items": {"type": "string"}},
        "asset_path": {"type": ["string", "null"]},
        "asset_url": {"type": ["string", "null"]},
        "caption": {"type": ["string", "null"]},
        "answer_index": {"type": ["integer", "null"], "minimum": 0, "maximum": 25},
        "component_id": {"type": ["string", "null"]},
        "component_type": {"type": ["string", "null"]},
        "component_ref": {"type": ["string", "null"]},
        "component_version": {"type": ["integer", "null"], "minimum": 1},
        "option_ids": {"type": "array", "items": {"type": "string"}},
        "component_data": {"type": ["object", "null"]},
    }


def _strict_block(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": _REQUIRED_BLOCK_FIELDS,
    }
