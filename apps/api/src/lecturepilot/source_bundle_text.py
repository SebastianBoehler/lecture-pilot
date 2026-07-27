from __future__ import annotations

from lecturepilot.bounded_sampling import evenly_sampled_indexes
from lecturepilot.canvas_models import CanvasBlock
from lecturepilot.latex_canvas_text import slug


MAX_TEXT_CHARS_PER_FILE = 12_000
MAX_PDF_TEXT_BLOCKS = 12


def text_blocks(source_ref: str, text: str) -> list[CanvasBlock]:
    return [
        CanvasBlock(
            id=f"{slug(source_ref)}-p-{index}",
            type="paragraph",
            text=paragraph,
        )
        for index, paragraph in enumerate(paragraphs(text)[:8], start=1)
    ]


def pdf_text_blocks(section_id: str, text: str) -> list[CanvasBlock]:
    values = paragraphs(text)
    selected = [values[index] for index in evenly_sampled_indexes(len(values), MAX_PDF_TEXT_BLOCKS)]
    return [
        CanvasBlock(id=f"{section_id}-p-{index}", type="paragraph", text=paragraph)
        for index, paragraph in enumerate(selected, start=1)
    ]


def heading(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("# ").strip()
    return None


def paragraphs(text: str) -> list[str]:
    cleaned = _strip_markdown_noise(text)[:MAX_TEXT_CHARS_PER_FILE]
    result = []
    for chunk in cleaned.split("\n\n"):
        paragraph = " ".join(line.strip() for line in chunk.splitlines() if line.strip())
        if len(paragraph.split()) >= 5:
            result.append(paragraph[:1800])
    return result


def _strip_markdown_noise(text: str) -> str:
    lines = []
    for line in text.replace("\r\n", "\n").splitlines():
        stripped = line.strip()
        if stripped.startswith("<!--"):
            continue
        lines.append(stripped.lstrip("# ").lstrip("> ").lstrip("-* "))
    return "\n".join(lines)
