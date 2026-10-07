from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from lecturepilot.agent_highlight import highlight_command_for
from lecturepilot.agent_image_placement import AgentImagePlacement
from lecturepilot.agent_tool_utils import required_str
from lecturepilot.raster_request_intent import is_explicit_raster_request
from lecturepilot.user_memory import UserMemoryStore


class AgentSideEffectError(RuntimeError):
    pass


class AgentSideEffectTools:
    def _highlight(self, span_id: str, highlight_text: str) -> dict[str, Any]:
        self.highlight_command = highlight_command_for(
            canvas_workspace=self.canvas_workspace,
            user_id=self.user_id,
            course_id=self.course_id,
            lecture_id=self.lecture_id,
            focus_section_id=self.focus_section_id,
            span_id=span_id,
            highlight_text=highlight_text,
        )
        return {
            "span_id": self.highlight_command.span_id,
            "highlight_text": self.highlight_command.highlight_text,
        }

    def _remember(self, args: dict[str, Any]) -> dict[str, Any]:
        if not _explicit_memory_request(self.user_message or ""):
            raise AgentSideEffectError(
                "Durable memory requires an explicit request from the learner."
            )
        key = str(args.get("preference_key") or "").strip() or None
        try:
            return UserMemoryStore(self.canvas_workspace.layout).remember(
                user_id=self.user_id,
                course_id=self.course_id,
                lecture_id=self.lecture_id,
                note=required_str(args, "note"),
                scope=str(args.get("scope") or "global"),
                preference_key=key,
                preference_value=str(args.get("preference_value") or "") if key else None,
            )
        except ValueError as exc:
            raise AgentSideEffectError(str(exc)) from exc

    def _generate_image(self, args: dict[str, Any]) -> dict[str, Any]:
        if not is_explicit_raster_request(self.user_message or ""):
            raise AgentSideEffectError(
                "Image generation requires an explicit raster image request from the learner."
            )
        usage_date = datetime.now(UTC).date()
        if self.usage_quota and self.tenant_id:
            self.usage_quota.consume_image(
                tenant_id=self.tenant_id,
                user_id=self.quota_user_id,
                course_id=self.course_id,
                usage_date=usage_date,
            )
        placement = self._image_placement()
        placement.focused_section_id = self.focus_section_id or self.initial_focus_section_id
        try:
            return placement.generate(args, image_generator=self.image_generator)
        except Exception:
            if self.usage_quota and self.tenant_id:
                self.usage_quota.refund_image(
                    tenant_id=self.tenant_id,
                    user_id=self.quota_user_id,
                    course_id=self.course_id,
                    usage_date=usage_date,
                )
            raise

    def pending_canvas_edit_instruction(self) -> str | None:
        return self.image_placement.pending_instruction() if self.image_placement else None

    def _clear_pending_image_insert(self, content: str) -> None:
        if self.image_placement:
            self.image_placement.mark_inserted(content)

    def _pending_image_write_error(self, logical_path: str, content: str) -> str | None:
        return (
            self.image_placement.write_rejection(logical_path, content)
            if self.image_placement
            else None
        )

    def _image_placement(self) -> AgentImagePlacement:
        if self.image_placement is None:
            self.image_placement = AgentImagePlacement(
                layout=self.canvas_workspace.layout,
                user_id=self.user_id,
                course_id=self.course_id,
                lecture_id=self.lecture_id,
                logical_for=self._logical_for,
                read_document=lambda: self.canvas_workspace.read_document(
                    course_id=self.course_id,
                    lecture_id=self.lecture_id,
                    user_id=self.user_id,
                ),
                focused_section_id=self.focus_section_id or self.initial_focus_section_id,
            )
        return self.image_placement


def _explicit_memory_request(message: str) -> bool:
    normalized = message.casefold().replace("’", "'")
    if re.search(
        r"\b(?:do not|don't|cannot|can't|never)\b.{0,40}\b(?:remember|save|explain)\b"
        r"|\b(?:merk(?:e)? dir|speicher\w*)\s+(?:bitte\s+)?(?:das\s+)?(?:nicht|nie)\b"
        r"|\b(?:nicht|nie)\s+(?:bitte\s+)?(?:merk(?:e)?|speicher\w*)\b",
        normalized,
    ):
        return False
    return bool(
        re.search(
            r"(?:^|[.!?;]\s*|\bplease\s+)(?:remember\s+(?:that|my|this|i)\b|save this preference\b|always explain\b)"
            r"|\b(?:can|could|will|would) you (?:please )?remember\b"
            r"|\b(?:merk(?:e)? dir|speicher(?:e)?)\b",
            normalized,
        )
    )
