from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any
from urllib.parse import parse_qs, urlparse

from lecturepilot.university_models import ExternalCourseCandidate, ExternalCourseSource


def _alma_courses(timetable: Any, *, term: str) -> list[ExternalCourseCandidate]:
    courses: list[ExternalCourseCandidate] = []
    seen_titles: set[str] = set()
    for raw in getattr(timetable, "occurrences", ()):
        title = _read(raw, "summary")
        title_key = _course_title_key(title)
        if not title or not title_key or title_key in seen_titles:
            continue
        seen_titles.add(title_key)
        courses.append(
            ExternalCourseCandidate(
                source=ExternalCourseSource.ALMA,
                external_course_id=_alma_title_id(term, title_key),
                term=term,
                title=title,
            )
        )
    return courses


def _ilias_courses(memberships: Any, *, term: str) -> list[ExternalCourseCandidate]:
    courses: list[ExternalCourseCandidate] = []
    for raw in memberships or ():
        display_url = _read(raw, "url")
        external_id = _ilias_course_id(display_url, _read(raw, "info_url"))
        title = _read(raw, "title")
        kind = (_read(raw, "kind") or "").casefold()
        if not external_id or not title or (kind and kind not in {"kurs", "course"}):
            continue
        courses.append(
            ExternalCourseCandidate(
                source=ExternalCourseSource.ILIAS,
                external_course_id=external_id,
                term=term,
                title=title,
                display_url=display_url,
            )
        )
    return courses


def _dedupe_courses(courses: list[ExternalCourseCandidate]) -> list[ExternalCourseCandidate]:
    deduped: dict[tuple[str, str, str], ExternalCourseCandidate] = {}
    for course in courses:
        key = (course.source.value, course.external_course_id, course.term)
        deduped.setdefault(key, course)
    return list(deduped.values())


def _alma_title_id(term: str, title_key: str) -> str:
    digest = hashlib.sha256(f"{term.casefold()}\0{title_key}".encode()).hexdigest()[:32]
    return f"title:{digest}"


def _course_title_key(value: str | None) -> str:
    normalized = unicodedata.normalize("NFKC", value or "").casefold()
    return "".join(character for character in normalized if character.isalnum())


def _ilias_course_id(*urls: str | None) -> str | None:
    for url in urls:
        if not url:
            continue
        match = re.search(r"/goto\.php/crs/(\d+)(?:/|$|[?#])", url)
        if match:
            return f"crs:{match.group(1)}"
        ref_id = next(iter(parse_qs(urlparse(url).query).get("ref_id", ())), "").strip()
        if ref_id.isdigit() and ("course" in url.casefold() or "type=crs" in url.casefold()):
            return f"crs:{ref_id}"
    return None


def _read(value: Any, field: str) -> str | None:
    if value is None:
        return None
    raw = value.get(field) if isinstance(value, dict) else getattr(value, field, None)
    return str(raw).strip() if raw not in (None, "") else None
