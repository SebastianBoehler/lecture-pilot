from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from dataclasses import dataclass
from typing import Any

from lecturepilot.ilias_identity import fetch_ilias_identity
from lecturepilot.tuebingen_courses import _alma_courses, _dedupe_courses, _ilias_courses
from lecturepilot.university_models import (
    ExternalCourseCandidate,
    ExternalCourseSource,
    UniversityLoginResult,
)


class TuebingenIntegrationUnavailable(RuntimeError):
    """Raised when the optional tue-api-wrapper package is missing."""


class TuebingenLoginError(RuntimeError):
    """Raised when university authentication cannot verify an account."""


@dataclass
class PendingUniversityLogin:
    client: Any
    initial_identity: UniversityLoginResult

    def synchronize(self) -> UniversityLoginResult:
        try:
            # Alma and ILIAS use independent authenticated sessions, so neither blocks the other.
            with ThreadPoolExecutor(max_workers=2, thread_name_prefix="university-sync") as pool:
                alma_future = pool.submit(
                    _load_alma_courses,
                    self.client.alma,
                    self.initial_identity.term,
                )
                ilias_future = pool.submit(
                    _load_ilias_account,
                    self.client.ilias,
                    self.initial_identity.term,
                )
                alma_courses, alma_checked, alma_warnings = alma_future.result()
                ilias = ilias_future.result()
        finally:
            with suppress(Exception):
                self.client.close()

        checked: set[ExternalCourseSource] = set()
        if alma_checked:
            checked.add(ExternalCourseSource.ALMA)
        if ilias.checked:
            checked.add(ExternalCourseSource.ILIAS)
        result = self.initial_identity.model_copy(
            update={
                "display_name": ilias.display_name,
                "email": ilias.email,
                "courses": _dedupe_courses([*alma_courses, *ilias.courses]),
                "sources_checked": checked,
                "warnings": [*alma_warnings, *ilias.warnings],
            }
        )
        return result


@dataclass(frozen=True)
class _IliasSync:
    courses: list[ExternalCourseCandidate]
    checked: bool
    display_name: str | None
    email: str | None
    warnings: list[str]


class TuebingenCourseAdapter:
    def authenticate(
        self,
        *,
        username: str,
        password: str,
        term: str,
    ) -> PendingUniversityLogin:
        client_type = _authenticated_client_type()
        try:
            client = client_type.login(username=username, password=password)
        except Exception as exc:
            raise TuebingenLoginError("University login failed.") from exc
        try:
            profile = client.alma.profile()
        except Exception as exc:
            client.close()
            raise TuebingenLoginError(
                "Alma account role could not be verified for this login."
            ) from exc
        return PendingUniversityLogin(
            client=client,
            initial_identity=UniversityLoginResult(
                username=username.strip(),
                term=term,
                alma_current_role=profile.current_role,
                alma_available_roles=list(profile.available_roles),
            ),
        )


def _load_alma_courses(
    api: Any,
    term: str,
) -> tuple[list[ExternalCourseCandidate], bool, list[str]]:
    try:
        timetable = api.timetable(term)
        courses = _alma_courses(timetable, term=term)
    except Exception:
        return [], False, ["Alma course enrollment data was unavailable for this login."]
    return courses, True, []


def _load_ilias_account(api: Any, term: str) -> _IliasSync:
    warnings: list[str] = []
    courses: list[ExternalCourseCandidate] = []
    checked = False
    display_name = None
    email = None
    try:
        memberships = api.memberships()
        courses = _ilias_courses(memberships, term=term)
    except Exception:
        warnings.append("ILIAS course membership data was unavailable for this login.")
    else:
        checked = True

    try:
        from tue_api_wrapper.ilias_client import ILIAS_ROOT_URL

        identity = fetch_ilias_identity(api.client, root_url=ILIAS_ROOT_URL)
        display_name = identity.display_name
        email = identity.email
    except Exception:
        warnings.append("ILIAS profile data was unavailable for this login.")
    return _IliasSync(courses, checked, display_name, email, warnings)


def _authenticated_client_type() -> Any:
    try:
        from tue_api_wrapper.sdk import TuebingenAuthenticatedClient
    except ImportError as exc:
        raise TuebingenIntegrationUnavailable(
            "tue-api-wrapper is not installed in the API environment. "
            'Install the backend with the "tuebingen" extra before live Uni login.'
        ) from exc
    return TuebingenAuthenticatedClient
