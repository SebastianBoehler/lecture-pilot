from __future__ import annotations

from typing import Any


def lecturepilot_response_format() -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "lecturepilot_agent_turn",
            "strict": True,
            "schema": _agent_turn_schema(),
        },
    }


def course_canvas_response_format() -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "lecturepilot_course_canvas",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "title": {"type": "string"},
                    "sections": {"type": "array", "items": _section_schema()},
                },
                "required": ["title", "sections"],
            },
        },
    }


def lecture_schedule_response_format() -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "lecturepilot_lecture_schedule",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "lectures": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "number": {"type": "string"},
                                "title": {"type": "string"},
                                "date": {"type": "string"},
                                "material_path": _nullable_string("Source file path for this lecture."),
                            },
                            "required": ["number", "title", "date", "material_path"],
                        },
                    },
                },
                "required": ["lectures"],
            },
        },
    }


def _agent_turn_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "message": {
                "type": "string",
                "description": "Student-facing tutor response.",
            },
            "session_goal": _nullable_string(
                "Active session goal, including a learner correction when provided."
            ),
            "canvas_commands": {
                "type": "array",
                "items": _canvas_command_schema(),
                "description": "Canvas navigation or learner-owned canvas updates.",
            },
            "quality_gate": _quality_gate_schema(),
        },
        "required": ["message", "session_goal", "canvas_commands", "quality_gate"],
    }


def _canvas_command_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "type": {
                "type": "string",
                "enum": [
                    "focus_section",
                    "highlight_span",
                    "open_artifact",
                    "append_section",
                    "update_section",
                ],
            },
            "section_id": _nullable_string("Existing or generated section id."),
            "span_id": _nullable_string("Existing canvas block id for precise highlight."),
            "highlight_text": _nullable_string("Short phrase from the highlighted block."),
            "artifact_id": _nullable_string("Artifact id for open_artifact commands."),
            "section": _nullable(_section_schema()),
            "placement": _nullable(_placement_schema()),
        },
        "required": [
            "type",
            "section_id",
            "span_id",
            "highlight_text",
            "artifact_id",
            "section",
            "placement",
        ],
    }


def _placement_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "mode": {"type": "string", "enum": ["after_section", "before_section"]},
            "section_id": {"type": "string"},
        },
        "required": ["mode", "section_id"],
    }


def _section_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "id": {"type": "string"},
            "title": {"type": "string"},
            "source_ref": _nullable_string("Source reference or student workspace."),
            "blocks": {"type": "array", "items": _block_schema()},
        },
        "required": ["id", "title", "source_ref", "blocks"],
    }


def _block_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "id": {"type": "string"},
            "type": {
                "type": "string",
                "enum": [
                    "paragraph",
                    "list",
                    "asset",
                    "callout",
                    "math",
                    "video",
                    "checkpoint",
                    "quiz",
                    "table",
                    "component",
                ],
            },
            "text": _nullable_string("Paragraph, formula, question, or prompt text."),
            "items": {"type": "array", "items": {"type": "string"}},
            "asset_path": _nullable_string("Course or learner asset path."),
            "asset_url": _nullable_string("Resolved learner asset URL."),
            "caption": _nullable_string("Caption for assets, callouts, or checks."),
            "answer_index": {"type": ["integer", "null"], "minimum": 0, "maximum": 25},
            "component_id": _nullable_string("File-backed component id."),
            "component_type": _nullable_string("Component renderer type."),
            "component_ref": _nullable_string("Component definition path."),
            "component_version": {"type": ["integer", "null"], "minimum": 1},
            "option_ids": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
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
        ],
    }


def _quality_gate_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "gate_id": {"type": "string"},
            "status": {"type": "string", "enum": ["passed", "needs_evidence", "not_assessed"]},
            "reason": {"type": "string"},
            "next_prompt": _nullable_string("Concrete next evidence request."),
        },
        "required": ["gate_id", "status", "reason", "next_prompt"],
    }


def _nullable(schema: dict[str, Any]) -> dict[str, Any]:
    result = dict(schema)
    result["type"] = [str(schema["type"]), "null"]
    return result


def _nullable_string(description: str) -> dict[str, Any]:
    return {"type": ["string", "null"], "description": description}
