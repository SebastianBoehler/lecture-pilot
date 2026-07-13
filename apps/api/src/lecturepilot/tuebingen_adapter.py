from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from typing import Any

from lecturepilot.auth_diagnostics import AuthDiagnostics, current_auth_diagnostics
from lecturepilot.ilias_identity import fetch_ilias_identity
from lecturepilot.tuebingen_courses import _alma_courses, _dedupe_courses, _ilias_courses
from lecturepilot.tuebingen_html_capture import (
    prepare_alma_html_capture,
    prepare_ilias_html_capture,
)
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
    diagnostics: AuthDiagnostics

    def synchronize(self) -> UniversityLoginResult:
        sync_started = self.diagnostics.started("university.sync")
        try:
            # Alma and ILIAS use independent authenticated sessions, so neither blocks the other.
            with ThreadPoolExecutor(max_workers=2, thread_name_prefix="university-sync") as pool:
                alma_future = pool.submit(
                    _load_alma_courses,
                    self.client.alma,
                    self.initial_identity.term,
                    self.diagnostics,
                )
                ilias_future = pool.submit(
                    _load_ilias_account,
                    self.client.ilias,
                    self.initial_identity.term,
                    self.diagnostics,
                )
                alma_courses, alma_checked, alma_warnings = alma_future.result()
                ilias = ilias_future.result()
        except Exception as exc:
            self.diagnostics.failed("university.sync", sync_started, exc)
            raise
        finally:
            close_started = self.diagnostics.started("wrapper.client_close")
            try:
                self.client.close()
            except Exception as exc:
                self.diagnostics.failed("wrapper.client_close", close_started, exc)
            else:
                self.diagnostics.succeeded("wrapper.client_close", close_started)

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
        self.diagnostics.succeeded(
            "university.sync",
            sync_started,
            course_count=len(result.courses),
            source_count=len(result.sources_checked),
            warning_count=len(result.warnings),
            display_name_present=result.display_name is not None,
            email_present=result.email is not None,
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
        diagnostics: AuthDiagnostics | None = None,
    ) -> PendingUniversityLogin:
        diagnostics = diagnostics or current_auth_diagnostics()
        client_type = _authenticated_client_type(diagnostics)
        client_started = diagnostics.started("wrapper.client_create")
        try:
            client = client_type.login(username=username, password=password)
        except Exception as exc:
            diagnostics.failed("wrapper.client_create", client_started, exc)
            raise TuebingenLoginError("University login failed.") from exc
        diagnostics.succeeded("wrapper.client_create", client_started)
        profile_started = diagnostics.started("alma.profile")
        try:
            prepare_alma_html_capture(client.alma, diagnostics)
            profile = client.alma.profile()
        except Exception as exc:
            diagnostics.failed("alma.profile", profile_started, exc)
            client.close()
            raise TuebingenLoginError(
                "Alma account role could not be verified for this login."
            ) from exc
        diagnostics.succeeded(
            "alma.profile",
            profile_started,
            current_role=profile.current_role,
            available_roles=list(profile.available_roles),
        )
        return PendingUniversityLogin(
            client=client,
            diagnostics=diagnostics,
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
    diagnostics: AuthDiagnostics,
) -> tuple[list[ExternalCourseCandidate], bool, list[str]]:
    started = diagnostics.started("alma.timetable")
    try:
        timetable = api.timetable(term)
        courses = _alma_courses(timetable, term=term)
    except Exception as exc:
        diagnostics.failed("alma.timetable", started, exc)
        return [], False, ["Alma course enrollment data was unavailable for this login."]
    diagnostics.succeeded(
        "alma.timetable",
        started,
        occurrence_count=len(getattr(timetable, "occurrences", ())),
        parsed_course_count=len(courses),
    )
    return courses, True, []


def _load_ilias_account(api: Any, term: str, diagnostics: AuthDiagnostics) -> _IliasSync:
    warnings: list[str] = []
    courses: list[ExternalCourseCandidate] = []
    checked = False
    display_name = None
    email = None
    login_started = diagnostics.started("ilias.login")
    try:
        prepare_ilias_html_capture(api, diagnostics)
    except Exception as exc:
        diagnostics.failed("ilias.login", login_started, exc)
        return _IliasSync(
            [], False, None, None, ["ILIAS account data was unavailable for this login."]
        )
    diagnostics.succeeded("ilias.login", login_started)

    memberships_started = diagnostics.started("ilias.memberships")
    try:
        memberships = api.memberships()
        courses = _ilias_courses(memberships, term=term)
    except Exception as exc:
        diagnostics.failed("ilias.memberships", memberships_started, exc)
        warnings.append("ILIAS course membership data was unavailable for this login.")
    else:
        checked = True
        diagnostics.succeeded(
            "ilias.memberships",
            memberships_started,
            membership_count=len(memberships or ()),
            parsed_course_count=len(courses),
        )

    identity_started = diagnostics.started("ilias.profile")
    try:
        from tue_api_wrapper.ilias_client import ILIAS_ROOT_URL

        identity = fetch_ilias_identity(api.client, root_url=ILIAS_ROOT_URL)
        display_name = identity.display_name
        email = identity.email
    except Exception as exc:
        diagnostics.failed("ilias.profile", identity_started, exc)
        warnings.append("ILIAS profile data was unavailable for this login.")
    else:
        diagnostics.succeeded(
            "ilias.profile",
            identity_started,
            display_name_present=display_name is not None,
            email_present=email is not None,
            email_domain=_email_domain(email),
        )
    return _IliasSync(courses, checked, display_name, email, warnings)


def _authenticated_client_type(diagnostics: AuthDiagnostics) -> Any:
    started = diagnostics.started("wrapper.import")
    try:
        from tue_api_wrapper.sdk import TuebingenAuthenticatedClient
    except ImportError as exc:
        diagnostics.failed("wrapper.import", started, exc)
        raise TuebingenIntegrationUnavailable(
            "tue-api-wrapper is not installed in the API environment. "
            'Install the backend with the "tuebingen" extra before live Uni login.'
        ) from exc
    diagnostics.succeeded("wrapper.import", started, wrapper_version=_wrapper_version())
    return TuebingenAuthenticatedClient


def _email_domain(email: str | None) -> str | None:
    return (email.rpartition("@")[2] or None) if email else None


def _wrapper_version() -> str:
    try:
        return version("tue-api-wrapper")
    except PackageNotFoundError:
        return "unknown"
