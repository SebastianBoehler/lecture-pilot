from __future__ import annotations

import re
from pathlib import Path

from lecturepilot.pdf_extract import read_pdf_text
from lecturepilot.source_index_models import IndexedSourceFile


MAX_EXCERPT_CHARS = 900
TEXT_KINDS = {"json", "latex", "markdown", "notebook", "python", "text"}


def source_file_excerpt(item: IndexedSourceFile, roots: list[Path]) -> str:
    path = _resolve_source(item.path, roots)
    if path is None:
        return "file contents unavailable"
    try:
        if item.kind == "pdf":
            return _compact(read_pdf_text(str(path), max_pages=3, max_chars=MAX_EXCERPT_CHARS))
        if item.kind in TEXT_KINDS:
            with path.open("r", encoding="utf-8", errors="ignore") as handle:
                return _compact(handle.read(MAX_EXCERPT_CHARS * 2))
    except (OSError, RuntimeError, ValueError):
        return "text extraction unavailable; use path and file metadata"
    return "binary asset; use path and surrounding course structure"


def _resolve_source(relative_path: str, roots: list[Path]) -> Path | None:
    for root in roots:
        candidate = root / relative_path
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def _compact(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()[:MAX_EXCERPT_CHARS] or "no text extracted"
