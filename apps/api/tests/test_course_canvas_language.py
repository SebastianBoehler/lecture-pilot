import json
from pathlib import Path


from auth_helpers import confirm_source_routing, professor_headers
from lecturepilot.course_builder_source import course_builder_source_document
from lecturepilot.course_workspace import resolve_course_workspace
from lecturepilot.models import CourseWorkspaceSetupInput
from test_course_workspace_api import _client


def test_professor_sets_and_persists_canvas_language(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = client.post(
        "/admin/course-workspaces",
        json={
            "canvas_language": "de",
            "course_title": "Bilingual ML Course",
            "lecture_number": "01",
            "lecture_title": "Introduction",
        },
        headers=professor_headers("prof-demo"),
    )

    assert response.status_code == 200
    assert response.json()["course"]["canvas_language"] == "de"
    stored = json.loads(
        (
            tmp_path
            / "workspaces"
            / "courses"
            / "tenant-tuebingen"
            / "bilingual-ml-course"
            / "builder"
            / "course-workspace.json"
        ).read_text(encoding="utf-8")
    )
    assert stored["course"]["canvas_language"] == "de"


def test_internal_course_updates_do_not_reset_the_selected_language() -> None:
    initial = resolve_course_workspace(
        CourseWorkspaceSetupInput(
            canvas_language="de",
            course_title="Bilingual ML Course",
        ),
        professor="prof-demo",
        term="Sommer 2026",
    )

    updated = resolve_course_workspace(
        CourseWorkspaceSetupInput(course_title="Bilingual ML Course"),
        professor="prof-demo",
        term="Sommer 2026",
        course=initial.course,
    )

    assert updated.course.canvas_language == "de"


def test_bilingual_uploads_remain_available_as_generation_evidence(tmp_path: Path) -> None:
    client = _client(tmp_path)
    created = client.post(
        "/admin/course-workspaces",
        json={
            "canvas_language": "de",
            "course_title": "Bilingual Evidence Course",
            "lecture_number": "01",
            "lecture_title": "Introduction",
        },
        headers=professor_headers("prof-demo"),
    )
    assert created.status_code == 200
    for path, content in (
        (
            "Lecture01-eng.md",
            b"# English source\n\nENGLISH-EVIDENCE explains the shared lecture topic clearly.",
        ),
        (
            "Lecture01.md",
            b"# Deutsche Quelle\n\nGERMAN-EVIDENCE erklaert das gemeinsame Vorlesungsthema klar.",
        ),
    ):
        uploaded = client.post(
            "/admin/courses/bilingual-evidence-course/materials",
            data={"path": path},
            files={"file": (path, content)},
            headers=professor_headers("prof-demo"),
        )
        assert uploaded.status_code == 200
    confirm_source_routing(client, "bilingual-evidence-course")

    source = course_builder_source_document(
        client.app,
        "bilingual-evidence-course",
        "lecture-01",
    )
    evidence = "\n".join(
        block.text or "" for section in source.sections for block in section.blocks
    )

    assert "ENGLISH-EVIDENCE" in evidence
    assert "GERMAN-EVIDENCE" in evidence
