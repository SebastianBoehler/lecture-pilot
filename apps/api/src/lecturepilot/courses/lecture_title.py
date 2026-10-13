"""Infer a lecture title from its primary source document.

Priority: the LaTeX ``\\title`` (or Markdown front-matter ``title``), without a leading
"Lecture NN:" / "Vorlesung NN:" numbering; then document metadata titles such as
``pdftitle``; then the first non-administrative section or frame heading.
"""

from __future__ import annotations

import re

_NUMBER_PREFIX = re.compile(
    r"^(?:lecture|lec\.?|vorlesung|vl|session|sitzung|einheit|unit|week|woche)"
    r"\s*0*\d{1,3}\s*(?:[:.\-–—|]\s*)?",
    re.IGNORECASE,
)
_HEADINGS = (
    r"\\section\*?\{([^{}]+)\}",
    r"\\begin\{frame\}(?:\[[^\]]*\])?\{([^{}]+)\}",
    r"\\frametitle\{([^{}]+)\}",
)
_ADMIN_TITLES = {"course thread", "feedback", "note", "plan", "requirements"}
_ADMIN_MARKERS = (
    "admin",
    "before we start",
    "consult",
    "evaluation",
    "klausur",
    "lehrevaluation",
    "outline",
    "rückmeldung",
)


def document_title(text: str, *, markdown: bool) -> str | None:
    if markdown:
        candidates = [_front_matter_title(text)]
        heading = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        if heading:
            title = clean_title(heading.group(1))
            candidates.append(_without_number(title) or title)
        return next((title for title in candidates if title), None)
    for title in (*_command_arguments(text, "title"), *_metadata_titles(text)):
        cleaned = _without_number(clean_title(_strip_latex(title)))
        if cleaned and not is_admin_title(cleaned):
            return cleaned
    for pattern in _HEADINGS:
        for match in re.finditer(pattern, text):
            title = clean_title(_strip_latex(match.group(1)))
            if title and not is_admin_title(title):
                return title
    return None


def clean_title(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\\\\", " ")).strip(" -")


def is_admin_title(title: str) -> bool:
    lowered = title.casefold()
    if lowered in _ADMIN_TITLES or lowered.startswith(("plan for", "recap and plan")):
        return True
    return any(marker in lowered for marker in _ADMIN_MARKERS)


def _command_arguments(text: str, command: str) -> list[str]:
    """Return the balanced mandatory argument of each ``\\command[...]{...}``."""
    values = []
    for match in re.finditer(rf"\\{command}\s*(?:\[[^\]]*\])?\s*\{{", text):
        depth, start = 1, match.end()
        for index in range(start, min(len(text), start + 2_000)):
            depth += {"{": 1, "}": -1}.get(text[index], 0)
            if depth == 0:
                values.append(text[start:index])
                break
    return values


def _metadata_titles(text: str) -> list[str]:
    return [
        match.group(1) or match.group(2)
        for match in re.finditer(r"pdftitle\s*=\s*(?:\{([^{}]+)\}|([^,}\n]+))", text)
    ]


def _front_matter_title(text: str) -> str | None:
    front = re.match(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", text, re.DOTALL)
    if not front:
        return None
    title = re.search(r"^title:\s*(.+)$", front.group(1), re.MULTILINE)
    return _without_number(clean_title(title.group(1).strip("'\""))) if title else None


def _strip_latex(value: str) -> str:
    value = re.sub(r"\\(?:\\|newline|linebreak)(?:\[[^\]]*\])?", " ", value)
    value = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?", " ", value)
    value = value.replace("\\&", "&").replace("~", " ")
    return value.replace("{", "").replace("}", "")


def _without_number(title: str) -> str:
    # A bare "Lecture 03" names no topic; the caller falls back to headings.
    return _NUMBER_PREFIX.sub("", title, count=1).strip(" -:")
