from types import SimpleNamespace

from lecturepilot.tuebingen_adapter import _alma_courses, _ilias_courses


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
