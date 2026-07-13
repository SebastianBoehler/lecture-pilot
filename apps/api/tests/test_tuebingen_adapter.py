import json
import logging
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from lecturepilot.auth_diagnostics import (
    AUTH_DIAGNOSTIC_LOGGER,
    AUTH_DIAGNOSTIC_PREFIX,
    auth_diagnostic_attempt,
)
from lecturepilot.ilias_identity import parse_ilias_identity_profile
from lecturepilot.tuebingen_adapter import TuebingenCourseAdapter
from lecturepilot.tuebingen_courses import _alma_courses, _ilias_courses
from lecturepilot.university_models import UniversityLoginResult


def test_alma_timetable_courses_use_stable_title_ids_without_detail_pages() -> None:
    timetable = SimpleNamespace(
        occurrences=[
            SimpleNamespace(summary="Secure Systems"),
            SimpleNamespace(summary="Secure Systems"),
            SimpleNamespace(summary="Probabilistic Machine Learning"),
        ]
    )

    courses = _alma_courses(timetable, term="Sommer 2026")

    assert [course.title for course in courses] == [
        "Secure Systems",
        "Probabilistic Machine Learning",
    ]
    assert all(course.external_course_id.startswith("title:") for course in courses)
    assert (
        courses[0].external_course_id
        == _alma_courses(
            SimpleNamespace(occurrences=[SimpleNamespace(summary="Secure Systems")]),
            term="Sommer 2026",
        )[0].external_course_id
    )


def test_ilias_memberships_require_stable_course_reference() -> None:
    memberships = [
        {
            "title": "Secure Systems",
            "kind": "course",
            "url": "https://ilias.example/goto.php/crs/67890",
        },
        {
            "title": "Ref Course",
            "kind": "Kurs",
            "url": "https://ilias.example/goto.php?target=crs&ref_id=2468&type=crs",
        },
        {
            "title": "Unstable Course",
            "kind": "course",
            "url": "https://ilias.example/course/no-id",
        },
    ]

    courses = _ilias_courses(memberships, term="Sommer 2026")

    assert [(course.external_course_id, course.title) for course in courses] == [
        ("crs:67890", "Secure Systems"),
        ("crs:2468", "Ref Course"),
    ]


def test_ilias_identity_profile_reads_account_managed_name_and_email() -> None:
    identity = parse_ilias_identity_profile(
        """
        <input id="usr_firstname" name="usr_firstname" value="Daniel">
        <input id="usr_lastname" name="usr_lastname" value="Example">
        <input id="usr_email" name="usr_email" value="daniel@example.edu">
        """
    )

    assert identity.display_name == "Daniel Example"
    assert identity.email == "daniel@example.edu"


def test_ilias_identity_profile_rejects_malformed_email() -> None:
    identity = parse_ilias_identity_profile(
        """
        <input id="usr_firstname" value="Daniel">
        <input id="usr_lastname" value="Example">
        <input id="usr_email" value="not an email">
        """
    )

    assert identity.display_name == "Daniel Example"
    assert identity.email is None


def test_authenticate_reads_server_verified_alma_role_before_course_sync(monkeypatch) -> None:
    client = _FakeClient()
    monkeypatch.setattr(
        "tue_api_wrapper.sdk.TuebingenAuthenticatedClient.login",
        lambda **_: client,
    )

    login = TuebingenCourseAdapter().authenticate(
        username="professor01",
        password="secret",
        term="Sommer 2026",
    )

    assert login.initial_identity.alma_current_role == "lecturer"
    assert login.initial_identity.alma_available_roles == ["lecturer", "examiner"]
    assert login.initial_identity.courses == []
    assert not client.closed

    result = login.synchronize()

    assert result.courses == []
    assert result.sources_checked == set()
    assert client.closed


def test_course_sync_preloads_identity_from_authenticated_ilias_profile(monkeypatch) -> None:
    client = _FakeClient()
    client.ilias = _IdentityIlias()
    monkeypatch.setattr(
        "tue_api_wrapper.sdk.TuebingenAuthenticatedClient.login",
        lambda **_: client,
    )

    login = TuebingenCourseAdapter().authenticate(
        username="professor01",
        password="secret",
        term="Sommer 2026",
    )
    result = login.synchronize()

    assert result.display_name == "Daniel Example"
    assert result.email == "daniel@example.edu"


def test_login_diagnostics_cover_provider_steps_without_personal_data(
    monkeypatch,
    caplog,
) -> None:
    monkeypatch.setenv("LECTUREPILOT_AUTH_DIAGNOSTICS", "true")
    client = _FakeClient()
    client.ilias = _IdentityIlias()
    monkeypatch.setattr(
        "tue_api_wrapper.sdk.TuebingenAuthenticatedClient.login",
        lambda **_: client,
    )

    with caplog.at_level(logging.WARNING, logger=AUTH_DIAGNOSTIC_LOGGER):
        with auth_diagnostic_attempt("professor01"):
            login = TuebingenCourseAdapter().authenticate(
                username="professor01",
                password="secret-password",
                term="Sommer 2026",
            )
            login.synchronize()

    events = [
        json.loads(message.removeprefix(AUTH_DIAGNOSTIC_PREFIX)) for message in caplog.messages
    ]
    successful_steps = {event["step"] for event in events if event["outcome"] == "succeeded"}
    assert {
        "wrapper.import",
        "wrapper.client_create",
        "alma.profile",
        "ilias.memberships",
        "ilias.profile",
        "wrapper.client_close",
        "university.sync",
    } <= successful_steps
    profile_event = next(
        event
        for event in events
        if event["step"] == "alma.profile" and event["outcome"] == "succeeded"
    )
    assert profile_event["current_role"] == "lecturer"
    serialized = "\n".join(caplog.messages)
    assert "professor01" not in serialized
    assert "secret-password" not in serialized
    assert "Daniel Example" not in serialized
    assert "daniel@example.edu" not in serialized


def test_university_role_claims_are_bounded() -> None:
    with pytest.raises(ValidationError):
        UniversityLoginResult(
            username="staff-user",
            term="Sommer 2026",
            alma_current_role="staff",
            alma_available_roles=["x" * 121],
        )


class _FakeClient:
    def __init__(self) -> None:
        self.alma = _FakeAlma()
        self.ilias = SimpleNamespace(memberships=_unavailable)
        self.closed = False

    def close(self) -> None:
        self.closed = True


class _FakeAlma:
    def profile(self):
        return SimpleNamespace(
            current_role="lecturer",
            available_roles=("lecturer", "examiner"),
        )

    def timetable(self, *_args, **_kwargs):
        raise RuntimeError("No staff timetable available")

    def timetable_course_assignments(self, *_args, **_kwargs):
        raise AssertionError("LecturePilot must not request enriched Alma course assignments")


def _unavailable():
    raise RuntimeError("No ILIAS memberships available")


class _IdentityIlias:
    def __init__(self) -> None:
        self.client = SimpleNamespace(
            session=_IdentitySession(),
            timeout_seconds=10,
        )

    def memberships(self):
        return []


class _IdentitySession:
    def get(self, url, **_kwargs):
        if "root/1" in url:
            html = (
                '<a href="/ilias.php?baseClass=ilDashboardGUI&amp;cmd=jumpToProfile">'
                "Profil und Datenschutz</a>"
            )
        else:
            html = """
                <input id="usr_firstname" value="Daniel">
                <input id="usr_lastname" value="Example">
                <input id="usr_email" value="daniel@example.edu">
            """
        return SimpleNamespace(
            text=html,
            url=url,
            raise_for_status=lambda: None,
        )
