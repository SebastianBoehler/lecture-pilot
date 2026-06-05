from __future__ import annotations

import re
from typing import Any

from lecturepilot.models import Course, TuebingenLoginResult


class TuebingenIntegrationUnavailable(RuntimeError):
    """Raised when the optional tue-api-wrapper package is missing."""


class TuebingenLoginError(RuntimeError):
    """Raised when Uni login or Alma timetable lookup fails."""


class TuebingenCourseAdapter:
    def login(self, *, username: str, password: str, term: str) -> TuebingenLoginResult:
        try:
            from tue_api_wrapper.sdk import TuebingenAuthenticatedClient
        except ImportError as exc:
            raise TuebingenIntegrationUnavailable(
                "tue-api-wrapper is not installed in the API environment. "
                'Install the backend with the "tuebingen" extra before live Uni login.'
            ) from exc

        client = TuebingenAuthenticatedClient.login(username=username, password=password)
        try:
            assignments = client.alma.timetable_course_assignments(term, limit=40)
            courses = _courses_from_assignments(assignments, term=term)
        except Exception as exc:
            raise TuebingenLoginError(
                "TUE API login failed or Alma did not return the timetable courses."
            ) from exc
        finally:
            client.close()

        return TuebingenLoginResult(username=username, term=term, courses=courses)


def _courses_from_assignments(assignments: Any, *, term: str) -> list[Course]:
    raw_courses = getattr(assignments, "courses", ())
    return [
        Course(
            id=_course_id(raw_course, index),
            title=_course_title(raw_course),
            professor=_course_professor(raw_course),
            term=term,
        )
        for index, raw_course in enumerate(raw_courses)
    ]


def _course_id(raw_course: Any, index: int) -> str:
    number = _read(raw_course, "number")
    title = _read(raw_course, "title") or _read(raw_course, "summary") or f"course-{index + 1}"
    slug_source = f"{number or ''} {title}".strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug_source.casefold()).strip("-")
    return f"alma-{slug or index + 1}"


def _course_title(raw_course: Any) -> str:
    title = _read(raw_course, "title") or _read(raw_course, "summary")
    number = _read(raw_course, "number")
    if title and number and not title.startswith(number):
        return f"{number} {title}"
    return title or number or "Untitled Alma course"


def _course_professor(raw_course: Any) -> str:
    return _read(raw_course, "organization") or _read(raw_course, "event_type") or "Unknown"


def _read(raw_course: Any, field: str) -> str | None:
    if isinstance(raw_course, dict):
        value = raw_course.get(field)
    else:
        value = getattr(raw_course, field, None)
    return str(value).strip() if value not in (None, "") else None
