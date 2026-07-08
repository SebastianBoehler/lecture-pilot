from __future__ import annotations

import re
from datetime import date, timedelta
from pathlib import Path

from lecturepilot.lecture_date_extraction import anchored_weekly_date, extract_source_date
from lecturepilot.models import LectureScheduleItem, LectureScheduleProposal
from lecturepilot.source_bundle import SourceBundleFile

LECTURE_FILE_RE = re.compile(r"(?:^|[/_-])lecture[-_ ]?0*(\d{1,2})(?:\D|$)", re.IGNORECASE)


def propose_lecture_schedule(
    *,
    course_id: str,
    files: list[SourceBundleFile],
    roots: list[Path],
    first_lecture_date: date | None = None,
    requested_count: int | None = None,
) -> LectureScheduleProposal:
    selected = _select_lecture_files(files)
    numbers = sorted(selected)
    if not numbers and requested_count:
        numbers = list(range(1, requested_count + 1))
    explicit_dates = _source_dates(numbers, selected, roots)
    default_start_date = first_lecture_date or date.today()
    lectures = [
        LectureScheduleItem(
            number=f"{number:02d}",
            title=_lecture_title(number, selected.get(number), roots),
            date=explicit_dates.get(index)
            or anchored_weekly_date(index=index, explicit_dates=explicit_dates, first_lecture_date=first_lecture_date)
            or default_start_date + timedelta(days=7 * index),
            material_path=selected.get(number).path if number in selected else None,
        )
        for index, number in enumerate(numbers or [1])
    ]
    return LectureScheduleProposal(
        course_id=course_id,
        lectures=lectures,
        source_paths=[item.path for item in selected.values()],
    )


def _select_lecture_files(files: list[SourceBundleFile]) -> dict[int, SourceBundleFile]:
    grouped: dict[int, list[SourceBundleFile]] = {}
    for item in files:
        match = LECTURE_FILE_RE.search(item.path)
        if match:
            grouped.setdefault(int(match.group(1)), []).append(item)
    return {number: sorted(items, key=_source_priority)[0] for number, items in grouped.items()}


def _source_dates(numbers: list[int], selected: dict[int, SourceBundleFile], roots: list[Path]) -> dict[int, date]:
    dates = {}
    for index, number in enumerate(numbers):
        source = selected.get(number)
        source_path = _resolve_source(source.path, roots) if source else None
        if source_path and (value := extract_source_date(source_path)):
            dates[index] = value
    return dates


def _source_priority(item: SourceBundleFile) -> tuple[int, int, str]:
    lowered = item.path.casefold()
    stale_penalty = 10 if "old" in lowered or "attic" in lowered else 0
    language_bonus = -2 if "-eng" in lowered else 0
    kind_priority = {"latex": 0, "markdown": 1, "text": 2, "pdf": 3}.get(item.kind, 4)
    return (stale_penalty + kind_priority + language_bonus, len(item.path), item.path)


def _lecture_title(number: int, source: SourceBundleFile | None, roots: list[Path]) -> str:
    if not source:
        return f"Lecture {number:02d}"
    source_path = _resolve_source(source.path, roots)
    if source_path and source_path.suffix.lower() in {".md", ".tex", ".txt"}:
        extracted = _extract_title(source_path)
        if extracted:
            return extracted
    return f"Lecture {number:02d}"


def _resolve_source(relative_path: str, roots: list[Path]) -> Path | None:
    for root in roots:
        candidate = root / relative_path
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def _extract_title(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8", errors="ignore")[:60_000]
    if path.suffix.lower() == ".md":
        heading = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        if heading:
            return _clean_title(heading.group(1))
    for pattern in (
        r"\\section\{([^{}]+)\}",
        r"\\begin\{frame\}\{([^{}]+)\}",
        r"\\frametitle\{([^{}]+)\}",
        r"\\title\{([^{}]+)\}",
    ):
        for match in re.finditer(pattern, text):
            title = _clean_title(match.group(1))
            if title and not _is_admin_title(title):
                return title
    return None


def _clean_title(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\\\\", " ")).strip(" -")


def _is_admin_title(title: str) -> bool:
    lowered = title.casefold()
    if lowered in {"course thread", "feedback", "note", "plan", "requirements"}:
        return True
    if lowered.startswith(("plan for", "recap and plan")):
        return True
    return any(
        marker in lowered
        for marker in ("admin", "before we start", "consult", "evaluation", "klausur", "lehrevaluation", "outline", "rückmeldung")
    )
