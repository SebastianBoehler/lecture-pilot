from __future__ import annotations

from typing import Literal


AgentToolProfile = Literal["tutor", "evidence", "course_builder"]

_PROFILE_TOOLS: dict[AgentToolProfile, tuple[str, ...]] = {
    "tutor": (
        "pwd",
        "ls",
        "read",
        "write",
        "edit",
        "focus",
        "highlight",
        "record_gate",
        "remember",
        "generate_image",
    ),
    "evidence": (
        "pwd",
        "ls",
        "find",
        "grep",
        "read",
        "write",
        "edit",
        "focus",
        "highlight",
        "record_gate",
        "remember",
        "generate_image",
    ),
    "course_builder": (
        "pwd",
        "ls",
        "find",
        "grep",
        "read",
        "write",
        "edit",
        "generate_image",
    ),
}


def agent_tool_schemas(profile: AgentToolProfile = "tutor") -> list[dict]:
    enabled = agent_tool_names(profile)
    return [schema for schema in _all_tool_schemas() if schema["function"]["name"] in enabled]


def agent_tool_names(profile: AgentToolProfile = "tutor") -> set[str]:
    return set(_PROFILE_TOOLS[profile])


def tutor_tool_profile_for_message(message: str) -> AgentToolProfile:
    lowered = message.lower()
    evidence_terms = ("source", "cite", "citation", "where", "find", "search", "exact", "evidence", "material")
    return "evidence" if any(term in lowered for term in evidence_terms) else "tutor"


def _all_tool_schemas() -> list[dict]:
    return [
        _tool("pwd", "Show the logical workspace roots available to the tutor.", {}),
        _tool(
            "ls",
            "List files or directories below a logical workspace path.",
            {"path": _string("Path such as /, /lecture/canvas, or /user/memories.")},
            ["path"],
        ),
        _tool(
            "find",
            "Find files below a logical workspace path by glob pattern.",
            {
                "path": _string("Directory to search."),
                "glob": _string("Glob pattern, for example *.md or **/*.yaml."),
                "max_results": _integer("Maximum result count.", 1, 80),
            },
            ["path"],
        ),
        _tool(
            "grep",
            "Search text files with a regular expression.",
            {
                "pattern": _string("Regular expression to search for."),
                "path": _string("Directory or file to search."),
                "max_matches": _integer("Maximum match count.", 1, 80),
            },
            ["pattern", "path"],
        ),
        _tool(
            "read",
            "Read a text file from the logical workspace.",
            {
                "path": _string("File path to read."),
                "max_chars": _integer("Maximum characters to return.", 200, 20000),
            },
            ["path"],
        ),
        _tool(
            "write",
            "Create or overwrite a permitted learner file. Canvas Markdown under /lecture/canvas/student is append-ordered and returns the actual path plus section_id.",
            {
                "path": _string("Writable file path under /lecture/canvas/student, /lecture/canvas/components, /lecture/canvas/student-assets, or /user/memories."),
                "content": _string("Complete file content."),
            },
            ["path", "content"],
        ),
        _tool(
            "edit",
            "Make an exact string replacement in a permitted learner file.",
            {
                "path": _string("Writable file path to edit."),
                "old_text": _string("Exact text to replace."),
                "new_text": _string("Replacement text."),
            },
            ["path", "old_text", "new_text"],
        ),
        _tool(
            "focus",
            "Move the lesson canvas to one existing section.",
            {"section_id": _string("Existing canvas section id.")},
            ["section_id"],
        ),
        _tool(
            "highlight",
            "Highlight one existing block or phrase in the lesson canvas.",
            {
                "span_id": _string("Existing block id."),
                "highlight_text": _string("Short phrase to highlight, if useful."),
            },
            ["span_id"],
        ),
        _tool(
            "record_gate",
            "Record the current learning-gate decision.",
            {
                "gate_id": _string("Stable gate id."),
                "status": {
                    "type": "string",
                    "enum": ["passed", "needs_evidence", "not_assessed"],
                },
                "reason": _string("Concise evidence-based reason."),
                "next_prompt": _string("Next concrete student check, if needed."),
            },
            ["gate_id", "status", "reason"],
        ),
        _tool(
            "remember",
            "Write a durable cross-course learner memory note.",
            {
                "note": _string("Preference or teaching-memory note to append."),
                "preference_key": _string("Optional structured preference key."),
                "preference_value": _string("Optional structured preference value."),
            },
            ["note"],
        ),
        _tool(
            "generate_image",
            "Generate a raster infographic asset in the learner canvas workspace.",
            {
                "prompt": _string("Image prompt grounded in the lecture material."),
                "section_id": _string("Section the infographic supports."),
                "filename": _string("Optional safe filename without extension."),
            },
            ["prompt"],
        ),
    ]


def _tool(
    name: str,
    description: str,
    properties: dict,
    required: list[str] | None = None,
) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required or [],
                "additionalProperties": False,
            },
        },
    }


def _string(description: str) -> dict:
    return {"type": "string", "description": description}


def _integer(description: str, minimum: int, maximum: int) -> dict:
    return {
        "type": "integer",
        "description": description,
        "minimum": minimum,
        "maximum": maximum,
    }
