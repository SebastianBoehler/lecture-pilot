from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from auth_helpers import professor_headers, student_headers
from canvas_workspace_fixtures import published_course_canvas
from lecturepilot.app import create_app
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.course_schedule_store import write_course_workspace
from lecturepilot.models import Course, CourseWorkspaceResult, Lecture


COURSE_ID = "lecture-access-course"
PAST_DATE = date(2020, 1, 1)
FUTURE_DATE = date(2099, 1, 1)
PAST_TIME = "2020-02-01T00:00:00Z"
FUTURE_TIME = "2099-12-01T00:00:00Z"


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "materials",
    )
    return TestClient(app)


def test_default_rule_and_course_mutation_authorization(client: TestClient) -> None:
    _seed_course(client, [("lecture-01", PAST_DATE)])

    initial = client.get(_course_access_url(), headers=professor_headers())
    assert initial.status_code == 200
    assert initial.json()["default_rule"] == {
        "audience": "tuebingen_enrolled",
        "publication_mode": "on_lecture_date",
        "publication_at": None,
    }
    assert initial.json()["lectures"][0]["rule_source"] == "course_default"

    unconfirmed = _put_course_rule(
        client,
        _rule("platform_authenticated", "on_lecture_date"),
        confirm=False,
    )
    assert unconfirmed.status_code == 400

    updated = _put_course_rule(
        client,
        _rule("platform_authenticated", "on_lecture_date"),
        confirm=True,
    )
    assert updated.status_code == 200
    assert updated.json()["default_rule"]["audience"] == "platform_authenticated"
    assert updated.json()["default_rule"]["publication_at"] is None

    denied = client.put(
        _course_access_url(),
        headers=_enrolled_headers(),
        json={"rule": _rule("instructors_only", "hidden"), "confirm_university_members": False},
    )
    assert denied.status_code == 403


def test_hidden_and_instructor_only_lectures_are_invisible(client: TestClient) -> None:
    lecture_ids = ("lecture-private", "lecture-hidden")
    _seed_course(client, [(lecture_id, PAST_DATE) for lecture_id in lecture_ids])
    for lecture_id in lecture_ids:
        _publish_canvas(client, lecture_id)
    assert (
        _put_lecture_rule(
            client,
            "lecture-private",
            _rule("instructors_only", "published_now"),
        ).status_code
        == 200
    )
    assert (
        _put_lecture_rule(
            client,
            "lecture-hidden",
            _rule("tuebingen_enrolled", "hidden"),
        ).status_code
        == 200
    )

    listed = client.get(f"/courses/{COURSE_ID}/lectures", headers=_enrolled_headers())
    assert listed.status_code == 200
    assert listed.json() == []
    for lecture_id in lecture_ids:
        for suffix in ("canvas/publication", "canvas", "learning-map", "asset.png"):
            prefix = "course-assets" if suffix == "asset.png" else "courses"
            path = (
                f"/{prefix}/{COURSE_ID}/{lecture_id}/{suffix}"
                if prefix == "course-assets"
                else f"/{prefix}/{COURSE_ID}/lectures/{lecture_id}/{suffix}"
            )
            assert client.get(path, headers=_enrolled_headers()).status_code == 404
    private_url = _lecture_access_url("lecture-private")
    assert client.delete(private_url, headers=_enrolled_headers()).status_code == 403
    restored = client.delete(private_url, headers=professor_headers())
    assert restored.status_code == 200
    assert restored.json()["rule_source"] == "course_default"
    assert _get_canvas(client, "lecture-private").status_code == 200


def test_scheduled_lecture_is_listed_but_content_is_locked(client: TestClient) -> None:
    _seed_course(client, [("lecture-future", FUTURE_DATE)])
    _publish_canvas(client, "lecture-future")

    listed = client.get(f"/courses/{COURSE_ID}/lectures", headers=_enrolled_headers())
    assert listed.status_code == 200
    item = listed.json()[0]
    assert item["lecture"]["id"] == "lecture-future"
    assert item["unlocked"] is False
    assert item["release_status"] == "scheduled"
    assert item["effective_publication_at"] == "2098-12-31T23:00:00Z"
    assert item["content_ready"] is True
    assert _get_canvas(client, "lecture-future").status_code == 403


def test_release_uses_later_of_lecture_date_and_custom_time(client: TestClient) -> None:
    lectures = [
        ("future-date", FUTURE_DATE),
        ("future-custom", PAST_DATE),
        ("released", PAST_DATE),
    ]
    _seed_course(client, lectures)
    for lecture_id, _ in lectures:
        _publish_canvas(client, lecture_id)
    rules = {
        "future-date": _rule("tuebingen_enrolled", "custom", PAST_TIME),
        "future-custom": _rule("tuebingen_enrolled", "custom", FUTURE_TIME),
        "released": _rule("tuebingen_enrolled", "custom", PAST_TIME),
    }
    for lecture_id, rule in rules.items():
        assert _put_lecture_rule(client, lecture_id, rule).status_code == 200

    assert _get_canvas(client, "future-date").status_code == 403
    assert _get_canvas(client, "future-custom").status_code == 403
    assert _get_canvas(client, "released").status_code == 200


def test_university_override_widens_course_discovery(client: TestClient) -> None:
    _seed_course(client, [("lecture-01", PAST_DATE)])
    _publish_canvas(client, "lecture-01")
    outsider = student_headers("outsider", course_ids=())

    before = client.get("/courses", headers=outsider)
    assert COURSE_ID not in {course["id"] for course in before.json()}
    assert client.get(f"/courses/{COURSE_ID}/lectures", headers=outsider).json() == []
    assert (
        _put_lecture_rule(
            client,
            "lecture-01",
            _rule("platform_authenticated", "published_now"),
            confirm=False,
        ).status_code
        == 400
    )

    widened = _put_lecture_rule(
        client,
        "lecture-01",
        _rule("platform_authenticated", "published_now"),
        confirm=True,
    )
    assert widened.status_code == 200
    assert widened.json()["rule_source"] == "lecture_override"
    assert widened.json()["rule"]["publication_at"].endswith(("Z", "+00:00"))
    after = client.get("/courses", headers=outsider)
    assert COURSE_ID in {course["id"] for course in after.json()}
    assert client.get(f"/courses/{COURSE_ID}/lectures", headers=outsider).status_code == 200
    assert _get_canvas(client, "lecture-01", headers=outsider).status_code == 200


def test_released_but_unpublished_content_remains_unavailable(client: TestClient) -> None:
    _seed_course(client, [("lecture-01", PAST_DATE)])
    asset = client.app.state.canvas_workspace.layout.course_uploads_dir(COURSE_ID) / "asset.png"
    asset.parent.mkdir(parents=True, exist_ok=True)
    asset.write_bytes(b"\x89PNG\r\n")

    listed = client.get(f"/courses/{COURSE_ID}/lectures", headers=_enrolled_headers())
    assert listed.status_code == 200
    assert listed.json() == []
    summary = client.get(_course_access_url(), headers=professor_headers())
    assert summary.status_code == 200
    assert summary.json()["lectures"][0]["release_status"] == "released"
    assert summary.json()["lectures"][0]["content_ready"] is False
    assert _get_canvas(client, "lecture-01").status_code == 404
    assert (
        client.get(
            f"/course-assets/{COURSE_ID}/lecture-01/asset.png",
            headers=_enrolled_headers(),
        ).status_code
        == 404
    )
    agent = client.post(
        "/agent/turn",
        headers=_enrolled_headers(),
        json={
            "course_id": COURSE_ID,
            "lecture_id": "lecture-01",
            "attendance": "present",
            "message": "Explain this lecture.",
        },
    )
    assert agent.status_code == 404


@pytest.mark.parametrize(
    ("publication_mode", "publication_at"),
    [
        ("custom", "2099-01-01T12:00:00"),
        ("custom", None),
        ("on_lecture_date", FUTURE_TIME),
    ],
)
def test_invalid_custom_publication_times_are_rejected(
    client: TestClient, publication_mode: str, publication_at: str | None
) -> None:
    _seed_course(client, [("lecture-01", PAST_DATE)])
    rule = _rule("tuebingen_enrolled", publication_mode, publication_at)
    response = _put_lecture_rule(client, "lecture-01", rule)
    assert response.status_code == 422


def _seed_course(client: TestClient, lectures: list[tuple[str, date]]) -> None:
    workspace = CourseWorkspaceResult(
        course=Course(
            id=COURSE_ID, title="Access Course", professor="Professor", term="Sommer 2026"
        ),
        lectures=[
            Lecture(id=lecture_id, course_id=COURSE_ID, title=lecture_id, date=lecture_date)
            for lecture_id, lecture_date in lectures
        ],
        active_lecture_id=lectures[0][0],
    )
    write_course_workspace(
        client.app.state.canvas_workspace.course_media_root(COURSE_ID), workspace
    )


def _publish_canvas(client: TestClient, lecture_id: str) -> None:
    client.app.state.canvas_workspace.write_course_canvas(
        published_course_canvas(COURSE_ID, lecture_id)
    )


def _rule(audience: str, publication_mode: str, publication_at: str | None = None) -> dict:
    return {
        "audience": audience,
        "publication_mode": publication_mode,
        **({"publication_at": publication_at} if publication_at is not None else {}),
    }


def _course_access_url() -> str:
    return f"/admin/courses/{COURSE_ID}/access"


def _lecture_access_url(lecture_id: str) -> str:
    return f"/admin/courses/{COURSE_ID}/lectures/{lecture_id}/access"


def _put_course_rule(client: TestClient, rule: dict, *, confirm: bool):
    return client.put(
        _course_access_url(),
        headers=professor_headers(),
        json={"rule": rule, "confirm_university_members": confirm},
    )


def _put_lecture_rule(client: TestClient, lecture_id: str, rule: dict, *, confirm: bool = False):
    return client.put(
        _lecture_access_url(lecture_id),
        headers=professor_headers(),
        json={"rule": rule, "confirm_university_members": confirm},
    )


def _enrolled_headers() -> dict[str, str]:
    return student_headers("student", course_ids=(COURSE_ID,))


def _get_canvas(client: TestClient, lecture_id: str, *, headers: dict[str, str] | None = None):
    return client.get(
        f"/courses/{COURSE_ID}/lectures/{lecture_id}/canvas",
        headers=headers or _enrolled_headers(),
    )
