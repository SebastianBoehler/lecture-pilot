from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from lecturepilot.tuebingen_adapter import TuebingenCourseAdapter, _alma_courses, _ilias_courses
from lecturepilot.university_models import UniversityLoginResult


def test_alma_memberships_require_stable_unit_id() -> None:
    assignments = SimpleNamespace(
        courses=[
            SimpleNamespace(
                title="Secure Systems",
                detail_url="https://alma.example/course?unitId=12345",
            ),
            SimpleNamespace(
                title="Unstable Course",
                detail_url="https://alma.example/course?title=unstable",
            ),
        ]
    )

    courses = _alma_courses(assignments, term="Sommer 2026")

    assert [(course.external_course_id, course.title) for course in courses] == [
        ("unit:12345", "Secure Systems")
    ]


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


def test_login_reads_server_verified_alma_role_even_without_course_data(monkeypatch) -> None:
    client = _FakeClient()
    monkeypatch.setattr(
        "tue_api_wrapper.sdk.TuebingenAuthenticatedClient.login",
        lambda **_: client,
    )

    result = TuebingenCourseAdapter().login(
        username="professor01",
        password="secret",
        term="Sommer 2026",
    )

    assert result.alma_current_role == "lecturer"
    assert result.alma_available_roles == ["lecturer", "examiner"]
    assert result.courses == []
    assert result.sources_checked == set()
    assert client.closed


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

    def timetable_course_assignments(self, *_args, **_kwargs):
        raise RuntimeError("No staff timetable available")


def _unavailable():
    raise RuntimeError("No ILIAS memberships available")
