import logging

from auth_helpers import professor_headers, student_headers
from learner_study_test_helpers import (
    COURSE_ID,
    HIDDEN_EVIDENCE,
    HIDDEN_QUIZ,
    learner,
    study_client,
)
from lecturepilot.canvas.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.learner.lecture_search import (
    MAX_RESULTS,
    SearchableLecture,
    normalize_query,
    search_lectures,
)

URL = f"/courses/{COURSE_ID}/search"


def test_search_returns_only_released_published_teaching_content(tmp_path, caplog) -> None:
    client = study_client(tmp_path)
    caplog.set_level(logging.DEBUG)

    response = client.get(URL, params={"q": "Posterior"}, headers=learner())

    assert response.status_code == 200, response.text
    results = response.json()["results"]
    assert {item["lecture_id"] for item in results} == {"lecture-open", "lecture-two"}
    assert results[0] == {
        "lecture_id": "lecture-two",
        "lecture_title": "Risk",
        "section_id": "posterior-risk",
        "section_title": "Posterior risk",
        "snippet": "Expected loss.",
    }
    intro = next(item for item in results if item["lecture_id"] == "lecture-open")
    assert intro["section_id"] == "intro"
    assert "posterior combines prior" in intro["snippet"]
    assert "**" not in intro["snippet"]
    server_logs = [
        record.getMessage() for record in caplog.records if "lecturepilot" in record.name
    ]
    assert server_logs
    assert not any("Posterior" in message for message in server_logs)


def test_search_never_matches_hidden_assessment_content(tmp_path) -> None:
    client = study_client(tmp_path)

    for hidden in (HIDDEN_EVIDENCE, HIDDEN_QUIZ):
        response = client.get(URL, params={"q": hidden}, headers=learner())
        assert response.status_code == 200
        assert response.json()["results"] == []


def test_search_enforces_course_access_and_query_bounds(tmp_path) -> None:
    client = study_client(tmp_path)

    assert client.get(URL, params={"q": "posterior"}).status_code == 401
    outsider = student_headers("outsider", course_ids=[])
    assert client.get(URL, params={"q": "posterior"}, headers=outsider).status_code == 404
    assert client.get(URL, params={"q": " a "}, headers=learner()).status_code == 422
    too_long = client.get(URL, params={"q": "x" * 101}, headers=learner())
    assert too_long.status_code == 422
    assert "xxxx" not in too_long.text
    unknown = client.get("/courses/missing-course/search", params={"q": "risk"}, headers=learner())
    assert unknown.status_code == 404


def test_course_owner_search_still_skips_locked_and_hidden_lectures(tmp_path) -> None:
    client = study_client(tmp_path)

    response = client.get(URL, params={"q": "posterior"}, headers=professor_headers())

    assert response.status_code == 200
    lecture_ids = {item["lecture_id"] for item in response.json()["results"]}
    assert lecture_ids == {"lecture-open", "lecture-two"}


def test_search_terms_are_bounded_and_results_capped() -> None:
    assert normalize_query("  Bayes   RULE bayes ") == ["bayes", "rule"]
    assert len(normalize_query(" ".join(f"t{index}" for index in range(20)))) == 8
    sections = [
        CanvasSection(
            id=f"s{index}",
            title=f"Section {index}",
            blocks=[CanvasBlock(id=f"b{index}", type="paragraph", text="shared term")],
        )
        for index in range(10)
    ]
    lectures = [
        SearchableLecture(
            id=f"l{index}",
            title=f"Lecture {index}",
            document=CanvasDocument(
                id=f"doc-{index}",
                course_id="c",
                lecture_id=f"l{index}",
                title="Doc",
                source_kind="generated",
                source_ref="fixture",
                workspace_path="course/index.md",
                sections=sections,
            ),
        )
        for index in range(6)
    ]

    result = search_lectures(lectures, ["shared"])

    assert len(result.results) == MAX_RESULTS
    assert result.truncated is True
    assert sum(item.lecture_id == "l0" for item in result.results) == 5
