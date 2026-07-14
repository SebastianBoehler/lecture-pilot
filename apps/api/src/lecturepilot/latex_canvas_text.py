from __future__ import annotations

import re

from lecturepilot.latex_canvas_assets import (
    BROWSER_ASSET_SUFFIXES,
    BROWSER_IMAGE_SUFFIXES,
    LATEX_ASSET_RE,
    is_allowed_canvas_asset,
)

__all__ = (
    "BROWSER_ASSET_SUFFIXES",
    "BROWSER_IMAGE_SUFFIXES",
    "is_allowed_canvas_asset",
)


def read_items(body: str) -> list[str]:
    items = [clean_inline(remove_display_math(item)) for item in _ITEM_RE.findall(body)]
    return unique([item for item in items if is_learning_text(item)])


def paragraphs_from_latex(body: str) -> list[str]:
    cleaned = remove_noisy_environments(body)
    cleaned = _ITEM_ENV_RE.sub(" ", cleaned)
    cleaned = LATEX_ASSET_RE.sub(" ", cleaned)
    cleaned = _MATH_BLOCK_RE.sub(" ", cleaned)
    chunks = re.split(r"\\\\|\\pause|\\sp\{[^}]*\}|\\vspace\{[^}]*\}|\n\s*\n", cleaned)
    paragraphs = [clean_inline(chunk) for chunk in chunks]
    return unique([text for text in paragraphs if is_learning_text(text)])


def read_math_blocks(body: str) -> list[str]:
    formulas = []
    for pattern in _MATH_PATTERNS:
        for match in pattern.finditer(body):
            formula = clean_formula(match.group("formula"))
            if formula:
                formulas.append(formula)
    return unique(formulas)


def clean_inline(text: str) -> str:
    text, formulas = protect_inline_math(text)
    text = text.replace("\\\\", " ")
    text = re.sub(r"\\(alert|textbf|underline|emph|term|Blue|Green)\{([^{}]*)\}", r"\2", text)
    text = re.sub(r"\\(?:only|onslide)<[^>]*>\{", " ", text)
    text = re.sub(r"\\(item|pause|homestudy|centering|newline|null|hfill)\b", " ", text)
    text = re.sub(r"\\(sp|col|column|stickynote|notationbox)(?:\[[^\]]*])?\{[^{}]*}", " ", text)
    text = re.sub(r"\\begin\{[^{}]+}|\\end\{[^{}]+}", " ", text)
    text = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*])?(?:\{[^{}]*})?", " ", text)
    text = text.replace("~", " ").replace("``", '"').replace("''", '"')
    text = text.replace("\\%", "%").replace("\\rightarrow", "->")
    text = re.sub(r"[{}]\s*|\s+", " ", text).strip()
    for token, formula in formulas.items():
        text = text.replace(token, formula)
    return text.strip()


def protect_inline_math(text: str) -> tuple[str, dict[str, str]]:
    formulas: dict[str, str] = {}

    def replace(match: re.Match[str]) -> str:
        token = f"@@MATH{len(formulas)}@@"
        formulas[token] = match.group(0)
        return token

    return _INLINE_MATH_RE.sub(replace, text), formulas


def clean_formula(formula: str) -> str:
    formula = re.sub(r"\\(pause|onslide|only)<[^>]*>", " ", formula)
    formula = re.sub(r"\\(Blue|Green|alert|textbf)\{([^{}]*)\}", r"\2", formula)
    formula = re.sub(r"\s+", " ", formula).strip()
    if _needs_aligned_wrapper(formula):
        return rf"\begin{{aligned}}{formula}\end{{aligned}}"
    return formula


def remove_noisy_environments(text: str) -> str:
    for env in ("tikzpicture", "tabular", "table", "figure"):
        text = re.sub(rf"\\begin\{{{env}}}.*?\\end\{{{env}}}", " ", text, flags=re.DOTALL)
    return text


def remove_display_math(text: str) -> str:
    text = _MATH_BLOCK_RE.sub(" ", text)
    return re.sub(r"[:;]\s*$|\s+", " ", text).strip()


def _needs_aligned_wrapper(formula: str) -> bool:
    if "\\begin{" in formula:
        return False
    return "&" in formula or "\\\\" in formula


def read_title(source: str) -> str | None:
    match = _TITLE_RE.search(source)
    return clean_inline(match.group("title")) if match else None


def strip_comments(source: str) -> str:
    return "\n".join(line for line in source.splitlines() if not line.lstrip().startswith("%"))


def slug(title: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", clean_inline(title).lower()).strip("-")
    return value[:80] or "section"


def is_skipped_frame_title(title: str) -> bool:
    normalized = title.lower()
    return normalized in {"note", "plan"} or "rückmeldung" in normalized or "feedback" in normalized


def is_learning_text(text: str) -> bool:
    return len(text.split()) >= 5 and not text.startswith(("@@MATH", "node[", "draw["))


def unique(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        normalized = value.lower()
        if normalized not in seen:
            seen.add(normalized)
            result.append(value)
    return result


_TITLE_RE = re.compile(r"\\mytitle(?:\[[^]]*])?\{[^{}]*}\{(?P<title>[^{}]+)}")
_ITEM_RE = re.compile(r"\\item\s+(.*?)(?=\\item|\\end\{itemize}|$)", re.DOTALL)
_ITEM_ENV_RE = re.compile(r"\\begin\{itemize}.*?\\end\{itemize}", re.DOTALL)
_INLINE_MATH_RE = re.compile(r"\$[^$\n]+\$|\\\([^)]*\\\)")
_MATH_BLOCK_RE = re.compile(
    r"\$\$.*?\$\$"
    r"|(?<!\\)\\\[.*?(?<!\\)\\\]"
    r"|\\begin\{(?:equation|align|myeqn)\*?}.*?\\end\{(?:equation|align|myeqn)\*?}",
    re.DOTALL,
)
_MATH_PATTERNS = (
    re.compile(r"\$\$(?P<formula>.*?)\$\$", re.DOTALL),
    re.compile(r"(?<!\\)\\\[(?P<formula>.*?)(?<!\\)\\\]", re.DOTALL),
    re.compile(
        r"\\begin\{(?:equation|align|myeqn)\*?}(?P<formula>.*?)\\end\{(?:equation|align|myeqn)\*?}",
        re.DOTALL,
    ),
)
