from __future__ import annotations

from typing import Any
from lecturepilot.agent_tool_schemas import AgentToolProfile


def _with_tool_instruction(
    messages: list[dict[str, str]], tool_profile: AgentToolProfile
) -> list[dict[str, str]]:
    result = [dict(message) for message in messages]
    result[0]["content"] += (
        " You can use Pi-style low-level tools over a constrained filesystem image. "
        "New learner canvas Markdown belongs under /lecture/canvas/student. Place custom explanations "
        "beside the relevant existing section using frontmatter placement_mode (after_section or "
        "before_section) and placement_section_id (the exact existing anchor id). Without explicit "
        "placement, new sections follow the current focused section. Preserve placement on edits. "
        "When write creates canvas Markdown, use the returned path and section_id for focus/highlight. "
        "Do not duplicate a successful write/edit/generate_image as an append_section or update_section "
        "in the final JSON; the filesystem tool output is the source of truth. "
        "For a chart, graph, plot, comparison, diagram, infographic, or visual explanation, prefer "
        "a trusted component such as visual_artifact and compose a flow, timeline, grid, or plot from "
        "validated data. Keep alternatives simultaneously visible when comparison is the point. "
        "Do not call generate_image as a fallback when a visual_artifact is difficult to express. "
        "Only call generate_image when the current student explicitly asks for a raster, pixel, "
        "photo, PNG, JPEG, or image asset. Place that image inside the best-fitting existing learner "
        "section. If none exists, write a meaningful explanation section first and then call "
        "generate_image with its returned section_id. "
        "Do not create a separate image-only section. "
        "Do not claim a raster image was added unless "
        "generate_image returned ok=true. If generate_image returns needs_canvas_edit=true, read the "
        "target section if needed, then use edit, not write, to insert the returned markdown directly "
        "after the sentence or bullet it explains before you answer. If you write Markdown that references the generated image, use the returned markdown "
        "or asset_url, not the logical path. "
        "Use focus/highlight tools to navigate attention. "
        "After tool use, return only the final LecturePilot JSON."
    )
    if result[-1]["role"] == "user":
        result[-1]["content"] += (
            f"\nActive tool profile: {tool_profile}. {_profile_instruction(tool_profile)}"
        )
    return result


def _profile_instruction(tool_profile: AgentToolProfile) -> str:
    if tool_profile == "evidence":
        return "Use find/grep/read when you need exact course evidence; write/edit stay learner-owned only."
    if tool_profile == "course_builder":
        return "Use find/grep/read/write/edit/generate_image for course-authoring workspace tasks."
    return "Use read for known paths; write/edit stay learner-owned only. Search tools are disabled in this profile."


def _tool_activity(name: str, args: dict[str, Any]) -> str:
    target = (
        args.get("path")
        or args.get("pattern")
        or args.get("section_id")
        or args.get("span_id")
        or args.get("block_id")
        or args.get("gate_id")
        or ""
    )
    return f"{name}: {str(target)[:80]}" if target else name
