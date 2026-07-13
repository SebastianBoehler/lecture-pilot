from fastapi.testclient import TestClient

from auth_helpers import professor_headers, student_headers
from lecturepilot.app import create_app
from lecturepilot.university_course_search import (
    UniversityCourseSearchError,
    UniversityCourseSuggestion,
)


class _Search:
    def __init__(self, *, fails: bool = False) -> None:
        self.fails = fails
        self.calls: list[tuple[str, str, int]] = []

    def search(self, *, query: str, term: str, limit: int):
        self.calls.append((query, term, limit))
        if self.fails:
            raise UniversityCourseSearchError("Alma search failed.")
        return [
            UniversityCourseSuggestion(
                title="Grundlagen des Maschinellen Lernens",
                number="INFO-1234",
                instructor="Prof. Example",
            )
        ]


def test_professor_can_search_public_alma_course_titles() -> None:
    app = create_app()
    search = _Search()
    app.state.university_course_search = search

    response = TestClient(app).get(
        "/admin/university-courses/search",
        params={"q": "Maschinelles", "term": "Sommer 2026", "limit": 6},
        headers=professor_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "title": "Grundlagen des Maschinellen Lernens",
                "number": "INFO-1234",
                "instructor": "Prof. Example",
            }
        ]
    }
    assert search.calls == [("Maschinelles", "Sommer 2026", 6)]


def test_public_alma_course_search_requires_professor_and_valid_query() -> None:
    app = create_app()
    app.state.university_course_search = _Search()
    client = TestClient(app)

    assert (
        client.get(
            "/admin/university-courses/search",
            params={"q": "Learning", "term": "Sommer 2026"},
            headers=student_headers(),
        ).status_code
        == 403
    )
    assert (
        client.get(
            "/admin/university-courses/search",
            params={"q": "ML", "term": "Sommer 2026"},
            headers=professor_headers(),
        ).status_code
        == 422
    )
    assert (
        client.get(
            "/admin/university-courses/search",
            params={"q": "   ", "term": "Sommer 2026"},
            headers=professor_headers(),
        ).status_code
        == 422
    )


def test_public_alma_course_search_reports_upstream_failure() -> None:
    app = create_app()
    app.state.university_course_search = _Search(fails=True)

    response = TestClient(app).get(
        "/admin/university-courses/search",
        params={"q": "Learning", "term": "Sommer 2026"},
        headers=professor_headers(),
    )

    assert response.status_code == 502
    assert response.json() == {"detail": "Alma course search is temporarily unavailable."}
