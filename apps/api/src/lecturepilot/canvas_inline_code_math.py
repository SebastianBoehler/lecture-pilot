"""Generated prose writes formulas as $...$; inline code would show students raw LaTeX."""

import re

from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.katex_commands import PORTABLE_KATEX_COMMANDS

_INLINE_CODE = re.compile(r"(?<!`)`([^`\n]+)`(?!`)")
_CONTROL_WORD = re.compile(r"\\([A-Za-z]+)")


def validate_inline_code_math(document: CanvasDocument) -> None:
    for section in document.sections:
        for block in section.blocks:
            # Code blocks hold real code; approved checkpoints are server-owned text.
            if block.type == "code" or block.id.startswith("practice-"):
                continue
            for text in [block.text or "", *(block.items or [])]:
                if span := latex_in_inline_code(text):
                    raise CanvasGenerationRepairableError(
                        f"Write math as $...$, not inline code: `{span}` in block {block.id} "
                        f"of {section.title}.",
                        section_id=section.id,
                        block_id=block.id,
                    )


def latex_in_inline_code(text: str) -> str | None:
    """Return the first inline-code span that holds a KaTeX command, e.g. `y \\in \\{0, 1\\}`."""
    for match in _INLINE_CODE.finditer(text):
        span = match.group(1)
        commands = set(_CONTROL_WORD.findall(span))
        if commands & PORTABLE_KATEX_COMMANDS or "\\{" in span:
            return span
    return None
