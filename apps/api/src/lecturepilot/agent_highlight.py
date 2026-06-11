from __future__ import annotations

from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.models import CanvasCommand
from lecturepilot.storage_layout import safe_id


def highlight_command_for(
    *,
    canvas_workspace: CanvasWorkspace,
    user_id: str,
    course_id: str,
    lecture_id: str,
    focus_section_id: str | None,
    span_id: str,
    highlight_text: str,
) -> CanvasCommand:
    phrase = highlight_text.strip()
    if phrase:
        match = _find_phrase_block(
            canvas_workspace=canvas_workspace,
            user_id=user_id,
            course_id=course_id,
            lecture_id=lecture_id,
            phrase=phrase,
        )
        if match:
            return CanvasCommand(
                type="highlight_span",
                section_id=match[0],
                span_id=match[1],
                highlight_text=phrase[:160],
            )
    return CanvasCommand(
        type="highlight_span",
        section_id=focus_section_id,
        span_id=safe_id(span_id),
        highlight_text=phrase[:160] or None,
    )


def _find_phrase_block(
    *,
    canvas_workspace: CanvasWorkspace,
    user_id: str,
    course_id: str,
    lecture_id: str,
    phrase: str,
) -> tuple[str, str] | None:
    document = canvas_workspace.read_document(course_id=course_id, lecture_id=lecture_id, user_id=user_id)
    needle = _compact(phrase)
    for section in document.sections:
        for block in section.blocks:
            haystack = _compact(" ".join([block.text or "", *block.items]))
            if needle and needle in haystack:
                return section.id, block.id
    return None


def _compact(value: str) -> str:
    return " ".join(value.casefold().split())
