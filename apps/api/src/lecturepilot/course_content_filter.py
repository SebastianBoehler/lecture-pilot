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
GLOBAL_COURSE_ADMIN_PATTERNS = (
    r"\boffizielle kursinfo\b",
    r"\bprüfungsinfo\b",
    r"\bthemen und materialien\b",
)


def filter_source_document_for_planning(document: CanvasDocument) -> CanvasDocument:
    lecture_sections = [
        section for section in document.sections if not _is_global_course_admin(section)
    ]
    sections = [section for section in lecture_sections if is_learning_section(section)]
    if len(sections) < 3:
        sections = lecture_sections
    return document.model_copy(update={"sections": sections})


def is_learning_section(section: CanvasSection) -> bool:
    normalized = _normalized_section_label(section)
    return not any(re.search(pattern, normalized) for pattern in LOW_VALUE_PATTERNS)


def _is_global_course_admin(section: CanvasSection) -> bool:
    normalized = _normalized_section_label(section)
    return any(re.search(pattern, normalized) for pattern in GLOBAL_COURSE_ADMIN_PATTERNS)


def _normalized_section_label(section: CanvasSection) -> str:
    text = " ".join(part for part in [section.title, section.source_ref or ""] if part)
    return re.sub(r"\s+", " ", text.lower())
