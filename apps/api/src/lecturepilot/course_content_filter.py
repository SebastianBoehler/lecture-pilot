from __future__ import annotations

import re

from lecturepilot.canvas_models import CanvasDocument, CanvasSection


LOW_VALUE_PATTERNS = (
    r"\badmin(?:istrative)?\b",
    r"\bcourse overview\b",
    r"\bprerequisites?\b",
    r"\brequirements?\b",
    r"\borganization\b",
    r"\bschedule\b",
    r"\bgrading\b",
    r"\bcredits?\b",
    r"\bliterature\b",
    r"consult the .*slides",
)


def filter_source_document_for_planning(document: CanvasDocument) -> CanvasDocument:
    sections = [section for section in document.sections if is_learning_section(section)]
    if len(sections) < 3:
        return document
    return document.model_copy(update={"sections": sections})


def is_learning_section(section: CanvasSection) -> bool:
    text = " ".join(
        part
        for part in [
            section.title,
            section.source_ref or "",
            *[
                block.text or block.caption or " ".join(block.items)
                for block in section.blocks[:3]
            ],
        ]
        if part
    )
    normalized = re.sub(r"\s+", " ", text.lower())
    return not any(re.search(pattern, normalized) for pattern in LOW_VALUE_PATTERNS)
