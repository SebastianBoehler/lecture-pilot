from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Callable

from lecturepilot.agent_image_targets import resolve_image_section_target
from lecturepilot.agent_image_tool import AgentImageToolError, generate_workspace_image
from lecturepilot.agent_tool_utils import required_str
from lecturepilot.storage_layout import safe_id


@dataclass
class PendingImageInsert:
    asset_url: str
    markdown: str
    section_id: str
    target_path: str

    def instruction(self) -> str:
        return (
            "The generated image asset is not visible on the canvas yet. "
            f"Use edit, not write, on {self.target_path} to insert this Markdown "
            f"right after the sentence or bullet it explains: {self.markdown}. "
            "Place it before examples, checkpoints, or section-end material when possible. "
            "Do not create a separate image-only section."
        )

    def is_satisfied_by(self, content: str) -> bool:
        return self.asset_url in content or self.markdown in content


class AgentImagePlacement:
    def __init__(
        self,
        *,
        layout: Any,
        user_id: str,
        course_id: str,
        lecture_id: str,
        logical_for: Callable[[Path], str],
        focused_section_id: str | None = None,
    ) -> None:
        self.layout = layout
        self.user_id = user_id
        self.course_id = course_id
        self.lecture_id = lecture_id
        self.logical_for = logical_for
        self.focused_section_id = focused_section_id
        self.pending: PendingImageInsert | None = None

    def generate(
        self,
        args: dict[str, Any],
        *,
        image_generator: Any | None,
    ) -> dict[str, Any]:
        prompt = required_str(args, "prompt")
        requested_id = str(args.get("section_id") or "").strip()
        requested_id = safe_id(requested_id) if requested_id else None
        canvas_dir = self.layout.user_canvas_dir(self.user_id, self.course_id, self.lecture_id)
        target = resolve_image_section_target(
            canvas_dir,
            requested_section_id=requested_id,
            focused_section_id=self.focused_section_id,
            prompt=prompt,
        )
        if target is None:
            raise AgentImageToolError(
                "No relevant existing learner section was found. Write the explanation "
                "section first, then generate the image for its returned section_id."
            )
        image = generate_workspace_image(
            image_generator=image_generator,
            layout=self.layout,
            user_id=self.user_id,
            course_id=self.course_id,
            lecture_id=self.lecture_id,
            prompt=prompt,
            section=target.section,
            filename=str(args.get("filename") or "") or None,
        )
        target_path = self.logical_for(target.path)
        self.pending = PendingImageInsert(
            asset_url=image["asset_url"],
            markdown=image["markdown"],
            section_id=target.section.id,
            target_path=target_path,
        )
        return {
            **image,
            "section_id": target.section.id,
            "target_path": target_path,
            "needs_canvas_edit": True,
        }

    def pending_instruction(self) -> str | None:
        return self.pending.instruction() if self.pending else None

    def mark_inserted(self, content: str) -> None:
        if self.pending and self.pending.is_satisfied_by(content):
            self.pending = None

    def write_rejection(self, logical_path: str, content: str) -> str | None:
        if not self.pending or not self.pending.is_satisfied_by(content):
            return None
        if logical_path == self.pending.target_path:
            return "Use edit, not write, to place the generated image at a precise anchor in the section."
        return f"Insert the generated image into {self.pending.target_path}; do not write it to another section."


def dedupe_markdown_image_refs(content: str) -> str:
    lines = content.splitlines()
    kept: list[str] = []
    seen_urls: set[str] = set()
    for line in reversed(lines):
        url = _markdown_image_url(line)
        if url and url in seen_urls:
            continue
        if url:
            seen_urls.add(url)
        kept.append(line)
    return "\n".join(reversed(kept)) + ("\n" if content.endswith("\n") else "")


def _markdown_image_url(line: str) -> str | None:
    match = re.match(r"^\s*!\[[^\]]*]\(([^)]+)\)\s*$", line)
    if not match:
        return None
    url = match.group(1)
    return url if "/student-assets/" in url else None
