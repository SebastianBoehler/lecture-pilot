import os

import pytest
from fastapi.testclient import TestClient

from api_test_client import workspace_client
from auth_helpers import professor_headers
from security_db_helpers import login, mutation_headers
from test_database_security import _app, _professor_login


def _course(api, access_policy="tuebingen_enrolled"):
    created = api.post(
        "/admin/course-workspaces",
        headers=professor_headers(),
        json={"course_title": "Medical Visualization", "access_policy": access_policy},
    )
    assert created.status_code == 200, created.text
    return created.json()["course"]["id"]


def test_professor_shares_rotates_and_disables_a_course_link(tmp_path):
    api = workspace_client(tmp_path)
    course_id = _course(api)
    assert api.get(f"/admin/courses/{course_id}/invite", headers=professor_headers()).json() is None
    invite = api.post(f"/admin/courses/{course_id}/invite", headers=professor_headers()).json()
    path = invite["path"]
    assert path.startswith(f"/join/{course_id}/") and len(path.rsplit("/", 1)[1]) >= 20
    assert (
        api.get(f"/admin/courses/{course_id}/invite", headers=professor_headers()).json() == invite
    )

    preview = api.get(path)
    assert preview.status_code == 200
    assert preview.json()["title"] == "Medical Visualization"
    assert api.get(path + "x").status_code == 404

    rotated = api.post(f"/admin/courses/{course_id}/invite", headers=professor_headers()).json()
    assert rotated != invite and api.get(path).status_code == 404
    assert (
        api.delete(f"/admin/courses/{course_id}/invite", headers=professor_headers()).status_code
        == 204
    )
    assert api.get(rotated["path"]).status_code == 404


def test_course_links_need_an_owner_and_shareable_audience(tmp_path):
    api = workspace_client(tmp_path)
    private = _course(api, access_policy="instructors_only")
    assert (
        api.post(f"/admin/courses/{private}/invite", headers=professor_headers()).status_code == 409
    )
    shared = _course(api)
    student = {**professor_headers("student01"), "X-User-Role": "student"}
    assert api.post(f"/admin/courses/{shared}/invite", headers=student).status_code == 403
    path = api.post(f"/admin/courses/{shared}/invite", headers=professor_headers()).json()["path"]
    assert api.post(path, headers=student).status_code == 409


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"), reason="PostgreSQL test database is not configured."
)
def test_joining_by_link_enrolls_a_student_without_alma(tmp_path):
    app = _app(tmp_path, {"owner": [], "student": []})
    owner_client = TestClient(app, base_url="http://localhost:8000")
    owner = _professor_login(app, owner_client, "owner")
    created = owner_client.post(
        "/admin/course-workspaces",
        headers=mutation_headers(owner),
        json={"course_title": "Medical Visualization", "access_policy": "tuebingen_enrolled"},
    )
    course_id = created.json()["course"]["id"]
    path = owner_client.post(
        f"/admin/courses/{course_id}/invite", headers=mutation_headers(owner)
    ).json()["path"]

    student_client = TestClient(app, base_url="http://localhost:8000")
    student = login(student_client, "student")
    assert course_id not in [course["id"] for course in student["courses"]]
    assert student_client.get(path).json()["lecture_count"] == 1
    joined = student_client.post(path, headers=mutation_headers(student))
    assert joined.status_code == 200, joined.text
    assert student_client.post(path, headers=mutation_headers(student)).status_code == 200
    courses = student_client.get("/me").json()["courses"]
    assert course_id in [course["id"] for course in courses]
