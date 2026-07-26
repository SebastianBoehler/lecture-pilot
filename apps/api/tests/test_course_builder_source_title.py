from pathlib import Path

from auth_helpers import professor_headers
from lecturepilot.course_builder_source import course_builder_source_document
from test_course_workspace_api import _client


def test_builder_source_uses_scheduled_lecture_title(tmp_path: Path) -> None:
    client = _client(tmp_path)
    created = client.post(
        "/admin/course-workspaces",
        json={
            "course_title": "Software Quality",
            "lecture_number": "04",
            "lecture_title": "White Box II: Logic Coverage",
        },
        headers=professor_headers(),
    )
    assert created.status_code == 200

    uploaded = client.post(
        "/admin/courses/software-quality/materials",
        data={"path": "uploads/12419_resource.md"},
        files={
            "file": (
                "12419_resource.md",
                b"# Generic LMS resource\n\nPredicate and clause coverage evidence.",
            )
        },
        headers=professor_headers(),
    )
    assert uploaded.status_code == 200

    source = course_builder_source_document(
        client.app,
        "software-quality",
        "lecture-04",
    )

    assert source.title == "White Box II: Logic Coverage"
