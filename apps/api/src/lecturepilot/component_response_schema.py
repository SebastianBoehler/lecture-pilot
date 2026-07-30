from __future__ import annotations

from typing import Any

from lecturepilot.canvas_component_catalog import SUPPORTED_COMPONENT_TYPES


def component_type_schema() -> dict[str, Any]:
    return {
        "type": ["string", "null"],
        "enum": [*SUPPORTED_COMPONENT_TYPES, None],
        "description": "Trusted component renderer type.",
    }


def component_data_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "chart_type": {
                "type": ["string", "null"],
                "enum": ["bar", "line", "scatter", "heatmap", None],
            },
            "control_type": {
                "type": ["string", "null"],
                "enum": ["buttons", "slider", None],
                "description": "Buttons for categorical states; slider for ordered numeric frames.",
            },
            "x_label": _nullable_string("Chart horizontal-axis label."),
            "y_label": _nullable_string("Chart vertical-axis label."),
            "control_label": _nullable_string("Label for the generated frame control."),
            "labels": {
                "type": "array",
                "items": {"type": "string"},
                "maxItems": 24,
            },
            "row_labels": {
                "type": "array",
                "items": {"type": "string"},
                "maxItems": 12,
            },
            "frames": {
                "type": "array",
                "maxItems": 12,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "label": {"type": "string"},
                        "values": {
                            "type": "array",
                            "items": {"type": "number"},
                            "maxItems": 24,
                        },
                        "points": {
                            "type": "array",
                            "maxItems": 120,
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "label": {"type": "string"},
                                    "x": {"type": "number"},
                                    "y": {"type": "number"},
                                    "series": _nullable_string("Optional point series."),
                                },
                                "required": ["label", "x", "y", "series"],
                            },
                        },
                        "matrix": {
                            "type": "array",
                            "maxItems": 12,
                            "items": {
                                "type": "array",
                                "items": {"type": "number"},
                                "maxItems": 12,
                            },
                        },
                        "explanation": {"type": "string"},
                    },
                    "required": ["label", "values", "points", "matrix", "explanation"],
                },
            },
            "steps": {
                "type": "array",
                "maxItems": 12,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "title": {"type": "string"},
                        "text": {"type": "string"},
                    },
                    "required": ["title", "text"],
                },
            },
        },
        "required": [
            "chart_type",
            "control_type",
            "x_label",
            "y_label",
            "control_label",
            "labels",
            "row_labels",
            "frames",
            "steps",
        ],
    }


def _nullable_string(description: str) -> dict[str, Any]:
    return {"type": ["string", "null"], "description": description}
