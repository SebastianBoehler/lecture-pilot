from __future__ import annotations

import re
from datetime import date
from pathlib import Path, PurePosixPath

from lecturepilot.lecture_date_extraction import extract_source_date
from lecturepilot.pdf_extract import read_pdf_text
from lecturepilot.source_bundle import SourceBundleFile


MAX_DETAIL_FILES = 36
MAX_EXCERPT_CHARS = 1200
TEXT_KINDS = {"code", "json", "latex", "markdown", "notebook", "text"}
DETAIL_KINDS = {*TEXT_KINDS, "pdf"}


def build_schedule_evidence(
    course_id: str,
    files: list[SourceBundleFile],
    roots: list[Path],
    first_lecture_date: date | None,
    requested_count: int | None,
) -> str:
    lines = [
        f"Course id: {course_id}",
        f"First lecture date: {_date_label(first_lecture_date)}",
        f"Requested count: {requested_count or 'infer from materials'}",
        f"Complete source inventory ({len(files)} files):",
    ]
    for item in sorted(files, key=lambda candidate: candidate.path.casefold()):
        lines.append(f"- path={item.path}; kind={item.kind}; size={item.size_bytes}")
    selected = _select_detail_files(files)
    lines.append(f"\nSelected content evidence ({len(selected)} representative files):")
    for item in selected:
        lines.append(_file_detail(item, roots))
    return "\n".join(lines)


def _select_detail_files(files: list[SourceBundleFile]) -> list[SourceBundleFile]:
    candidates = [item for item in files if item.kind in DETAIL_KINDS]
    return sorted(candidates, key=_detail_priority)[:MAX_DETAIL_FILES]


def _detail_priority(item: SourceBundleFile) -> tuple[int, int, str]:
    depth = len(PurePosixPath(item.path).parts)
    return (depth, -item.size_bytes, item.path.casefold())


def _file_detail(item: SourceBundleFile, roots: list[Path]) -> str:
    base = f"- path={item.path}; kind={item.kind}; size={item.size_bytes}"
    path = _resolve_source(item.path, roots)
    if path is None:
        return base
    try:
        date_cue = extract_source_date(path)
        text = _read_source_text(path, item.kind)
    except (OSError, RuntimeError, ValueError):
        return f"{base}\n  content: unavailable"
    return (
        f"{base}\n"
        f"  date cue: {date_cue.isoformat() if date_cue else 'none detected'}\n"
        f"  outline: {_outline(text, item.kind)}\n"
        f"  excerpt: {_compact(text)}"
    )


def _read_source_text(path: Path, kind: str) -> str:
    if kind == "pdf":
        return read_pdf_text(str(path), max_pages=3, max_chars=MAX_EXCERPT_CHARS)
    return path.read_text(encoding="utf-8", errors="ignore")[:MAX_EXCERPT_CHARS]


def _resolve_source(relative_path: str, roots: list[Path]) -> Path | None:
    for root in roots:
        candidate = root / relative_path
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def _date_label(value: date | None) -> str:
    return value.isoformat() if value else date.today().isoformat()


def _compact(text: str) -> str:
    return (
        " ".join(line.strip() for line in text.splitlines() if line.strip())[:MAX_EXCERPT_CHARS]
        or "no text extracted"
    )


def _outline(text: str, kind: str) -> str:
    if kind == "latex":
        titles = [
            _clean_title(match.group(1))
            for pattern in (
                r"\\section\{([^{}]+)\}",
                r"\\begin\{frame\}\{([^{}]+)\}",
                r"\\frametitle\{([^{}]+)\}",
            )
            for match in re.finditer(pattern, text)
        ]
    elif kind == "markdown":
        titles = [
            _clean_title(match.group(1))
            for match in re.finditer(r"^#{1,3}\s+(.+)$", text, re.MULTILINE)
        ]
    else:
        titles = []
    unique = list(dict.fromkeys(title for title in titles if title))
    return "; ".join(unique[:24]) or "no structured outline detected"


def _clean_title(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\\\\", " ")).strip(" -")
