from __future__ import annotations

import re
from datetime import date, timedelta
from pathlib import Path


MAX_DATE_SCAN_CHARS = 80_000
MAX_PDF_DATE_PAGES = 5

MONTHS = {
    "jan": 1,
    "january": 1,
    "januar": 1,
    "feb": 2,
    "february": 2,
    "februar": 2,
    "mar": 3,
    "march": 3,
    "märz": 3,
    "maerz": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "mai": 5,
    "jun": 6,
    "june": 6,
    "juni": 6,
    "jul": 7,
    "july": 7,
    "juli": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "okt": 10,
    "oktober": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
    "dez": 12,
    "dezember": 12,
}

DATE_COMMAND_RE = re.compile(r"\\(?:date|subtitle|author)\s*\{([^{}]{4,120})\}", re.IGNORECASE)
ISO_DATE_RE = re.compile(r"\b(20\d{2})[-/](0?[1-9]|1[0-2])[-/](0?[1-9]|[12]\d|3[01])\b")
EU_DATE_RE = re.compile(r"\b(0?[1-9]|[12]\d|3[01])\.(0?[1-9]|1[0-2])\.(20\d{2})\b")
MONTH_DATE_RE = re.compile(
    r"\b("
    + "|".join(sorted(MONTHS, key=len, reverse=True))
    + r")\.?\s+([0-3]?\d),?\s+(20\d{2})\b",
    re.IGNORECASE,
)
DATE_MONTH_RE = re.compile(
    r"\b([0-3]?\d)\.?\s+("
    + "|".join(sorted(MONTHS, key=len, reverse=True))
    + r")\.?\s+(20\d{2})\b",
    re.IGNORECASE,
)


def extract_source_date(path: Path) -> date | None:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return parse_date_text(_pdf_text(path))
    if suffix not in {".tex", ".md", ".txt", ".json"}:
        return None
    text = path.read_text(encoding="utf-8", errors="ignore")[:MAX_DATE_SCAN_CHARS]
    candidates = []
    candidates.extend(match.group(1) for match in DATE_COMMAND_RE.finditer(text))
    candidates.append(text[:8000])
    for candidate in candidates:
        if value := parse_date_text(candidate):
            return value
    return None


def parse_date_text(text: str) -> date | None:
    cleaned = re.sub(r"\\(?:today|semester|term)\b", " ", text, flags=re.IGNORECASE)
    for match in ISO_DATE_RE.finditer(cleaned):
        if value := _date(int(match.group(1)), int(match.group(2)), int(match.group(3))):
            return value
    for match in EU_DATE_RE.finditer(cleaned):
        if value := _date(int(match.group(3)), int(match.group(2)), int(match.group(1))):
            return value
    for match in MONTH_DATE_RE.finditer(cleaned):
        month = MONTHS[match.group(1).casefold()]
        if value := _date(int(match.group(3)), month, int(match.group(2))):
            return value
    for match in DATE_MONTH_RE.finditer(cleaned):
        month = MONTHS[match.group(2).casefold()]
        if value := _date(int(match.group(3)), month, int(match.group(1))):
            return value
    return None


def anchored_weekly_date(
    *,
    index: int,
    explicit_dates: dict[int, date],
    first_lecture_date: date | None,
) -> date | None:
    if first_lecture_date:
        return first_lecture_date + timedelta(days=7 * index)
    if not explicit_dates:
        return None
    anchor_index, anchor_date = min(explicit_dates.items(), key=lambda item: item[0])
    return anchor_date + timedelta(days=7 * (index - anchor_index))


def _date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _pdf_text(path: Path) -> str:
    try:
        import fitz
    except ImportError:
        return ""
    try:
        document = fitz.open(path)
    except Exception:
        return ""
    try:
        pages = [document.load_page(index).get_text("text") for index in range(min(len(document), MAX_PDF_DATE_PAGES))]
        return "\n\n".join(pages)[:MAX_DATE_SCAN_CHARS]
    finally:
        document.close()
