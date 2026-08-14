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
                            "items": _point_schema(),
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
            "visual_layout": {
                "type": ["string", "null"],
                "enum": ["flow", "timeline", "grid", "plot", None],
            },
            "visual_nodes": {
                "type": "array",
                "maxItems": 12,
                "items": _visual_node_schema(),
            },
            "visual_edges": {
                "type": "array",
                "maxItems": 16,
                "items": _visual_edge_schema(),
            },
            "visual_series": {
                "type": "array",
                "maxItems": 6,
                "items": _visual_series_schema(),
            },
            "visual_annotations": {
                "type": "array",
                "maxItems": 12,
                "items": _visual_annotation_schema(),
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
            "visual_layout",
            "visual_nodes",
            "visual_edges",
            "visual_series",
            "visual_annotations",
        ],
    }


def _visual_node_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "id": {"type": "string"},
            "label": {"type": "string"},
            "detail": {"type": "string"},
            "value": {"type": ["string", "null"]},
        },
        "required": ["id", "label", "detail", "value"],
    }


def _visual_edge_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "from_id": {"type": "string"},
            "to_id": {"type": "string"},
            "label": {"type": ["string", "null"]},
        },
        "required": ["from_id", "to_id", "label"],
    }


def _visual_series_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "label": {"type": "string"},
            "mark": {"type": "string", "enum": ["line", "bar", "point"]},
            "points": {"type": "array", "maxItems": 24, "items": _point_schema()},
        },
        "required": ["label", "mark", "points"],
    }


def _point_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "label": {"type": "string"},
            "x": {"type": "number"},
            "y": {"type": "number"},
            "series": _nullable_string("Optional point series."),
        },
        "required": ["label", "x", "y", "series"],
    }


def _visual_annotation_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "label": {"type": "string"},
            "target_id": {"type": ["string", "null"]},
        },
        "required": ["label", "target_id"],
    }


def _nullable_string(description: str) -> dict[str, Any]:
    return {"type": ["string", "null"], "description": description}
