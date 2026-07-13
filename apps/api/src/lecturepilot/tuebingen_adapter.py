from __future__ import annotations

import re
from typing import Any
from urllib.parse import parse_qs, urlparse

from lecturepilot.ilias_identity import fetch_ilias_identity
from lecturepilot.university_models import (
    ExternalCourseCandidate,
    ExternalCourseSource,
    UniversityLoginResult,
)


class TuebingenIntegrationUnavailable(RuntimeError):
    """Raised when the optional tue-api-wrapper package is missing."""


class TuebingenLoginError(RuntimeError):
    """Raised when university authentication or course lookup fails."""


class TuebingenCourseAdapter:
    def login(self, *, username: str, password: str, term: str) -> UniversityLoginResult:
        try:
            from tue_api_wrapper.sdk import TuebingenAuthenticatedClient
        except ImportError as exc:
            raise TuebingenIntegrationUnavailable(
                "tue-api-wrapper is not installed in the API environment. "
                'Install the backend with the "tuebingen" extra before live Uni login.'
            ) from exc

        try:
            client = TuebingenAuthenticatedClient.login(username=username, password=password)
        except Exception as exc:
            raise TuebingenLoginError("University login failed.") from exc
        courses: list[ExternalCourseCandidate] = []
        checked: set[ExternalCourseSource] = set()
        warnings: list[str] = []
        display_name: str | None = None
        email: str | None = None
        try:
            try:
                profile = client.alma.profile()
            except Exception as exc:
                raise TuebingenLoginError(
                    "Alma account role could not be verified for this login."
                ) from exc
            try:
                assignments = client.alma.timetable_course_assignments(term, limit=80)
                courses.extend(_alma_courses(assignments, term=term))
                checked.add(ExternalCourseSource.ALMA)
            except Exception:
                warnings.append("Alma course enrollment data was unavailable for this login.")
            try:
                memberships = client.ilias.memberships()
                courses.extend(_ilias_courses(memberships, term=term))
                checked.add(ExternalCourseSource.ILIAS)
            except Exception:
                warnings.append("ILIAS course membership data was unavailable for this login.")
            else:
                try:
                    from tue_api_wrapper.ilias_client import ILIAS_ROOT_URL

                    identity = fetch_ilias_identity(client.ilias.client, root_url=ILIAS_ROOT_URL)
                    display_name = identity.display_name
                    email = identity.email
                except Exception:
                    warnings.append("ILIAS profile data was unavailable for this login.")
        finally:
            client.close()

        return UniversityLoginResult(
            username=username.strip(),
            display_name=display_name,
            email=email,
            term=term,
            alma_current_role=profile.current_role,
            alma_available_roles=list(profile.available_roles),
            courses=_dedupe_courses(courses),
            sources_checked=checked,
            warnings=warnings,
        )


def _alma_courses(assignments: Any, *, term: str) -> list[ExternalCourseCandidate]:
    courses: list[ExternalCourseCandidate] = []
    for raw in getattr(assignments, "courses", ()):
        detail = getattr(raw, "detail", None)
        display_url = _read(raw, "detail_url") or _read(detail, "permalink")
        external_id = _alma_course_id(display_url)
        title = _read(raw, "title") or _read(raw, "summary")
        if not external_id or not title:
            continue
        courses.append(
            ExternalCourseCandidate(
                source=ExternalCourseSource.ALMA,
                external_course_id=external_id,
                term=term,
                number=_read(raw, "number"),
                title=title,
                organization=_read(raw, "organization"),
                display_url=display_url,
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


def _alma_course_id(*urls: str | None) -> str | None:
    for url in urls:
        if not url:
            continue
        query = parse_qs(urlparse(url).query)
        unit_id = next(iter(query.get("unitId", ())), "").strip()
        if unit_id.isdigit():
            return f"unit:{unit_id}"
    return None


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


def _dedupe_courses(courses: list[ExternalCourseCandidate]) -> list[ExternalCourseCandidate]:
    deduped: dict[tuple[str, str, str], ExternalCourseCandidate] = {}
    for course in courses:
        key = (course.source.value, course.external_course_id, course.term)
        deduped.setdefault(key, course)
    return list(deduped.values())


def _read(value: Any, field: str) -> str | None:
    if value is None:
        return None
    raw = value.get(field) if isinstance(value, dict) else getattr(value, field, None)
    return str(raw).strip() if raw not in (None, "") else None
