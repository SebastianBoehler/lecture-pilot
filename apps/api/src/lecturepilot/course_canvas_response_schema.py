from __future__ import annotations

from typing import Any

from lecturepilot.component_response_schema import component_data_schema


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
    return _strict_object(
        {
            "title": {"type": "string"},
            "blocks": {"type": "array", "items": _block_schema()},
        }
    )


def _block_schema() -> dict[str, Any]:
    return {
        "anyOf": [
            *(_text_block_schema(kind) for kind in ("paragraph", "callout", "math")),
            _list_schema(),
            *(_asset_schema(kind) for kind in ("asset", "video")),
            *(_captioned_text_schema(kind) for kind in ("checkpoint", "table")),
            _quiz_schema(),
            _single_choice_schema(),
            _data_component_schema("interactive_chart"),
            _data_component_schema("process_explorer"),
            _data_component_schema("visual_artifact"),
            _data_component_schema("mechanism_comparison"),
        ]
    }


def _text_block_schema(kind: str) -> dict[str, Any]:
    return _strict_object({"type": _const(kind), "text": {"type": "string"}})


def _list_schema() -> dict[str, Any]:
    return _strict_object(
        {
            "type": _const("list"),
            "items": {"type": "array", "items": {"type": "string"}},
        }
    )


def _asset_schema(kind: str) -> dict[str, Any]:
    return _strict_object(
        {
            "type": _const(kind),
            "asset_path": {"type": "string"},
            "caption": {"type": "string"},
        }
    )


def _captioned_text_schema(kind: str) -> dict[str, Any]:
    return _strict_object(
        {
            "type": _const(kind),
            "text": {"type": "string"},
            "caption": {"type": "string"},
        }
    )


def _quiz_schema() -> dict[str, Any]:
    return _strict_object(
        {
            "type": _const("quiz"),
            "text": {"type": "string"},
            "items": {"type": "array", "items": {"type": "string"}, "minItems": 2},
            "answer_index": {"type": "integer", "minimum": 0, "maximum": 25},
        }
    )


def _single_choice_schema() -> dict[str, Any]:
    return _strict_object(
        {
            **_component_properties("single_choice_quiz"),
            "items": {"type": "array", "items": {"type": "string"}, "minItems": 2},
            "option_ids": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 2,
            },
            "answer_index": {"type": "integer", "minimum": 0, "maximum": 25},
        }
    )


def _data_component_schema(component_type: str) -> dict[str, Any]:
    return _strict_object(
        {
            **_component_properties(component_type),
            "component_data": component_data_schema(),
        }
    )


def _component_properties(component_type: str) -> dict[str, Any]:
    return {
        "type": _const("component"),
        "text": {"type": "string"},
        "caption": {"type": "string"},
        "component_id": {"type": "string"},
        "component_type": _const(component_type),
        "component_version": {"type": "integer", "minimum": 1},
    }


def _strict_object(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": list(properties),
    }


def _const(value: str) -> dict[str, Any]:
    return {"type": "string", "const": value}
