import json
from pathlib import Path

import pytest

from auth_helpers import professor_headers
from canvas_workspace_fixtures import published_course_canvas
from lecturepilot.course_canvas_prompt import planner_messages, repair_message
from lecturepilot.course_canvas_section_prompt import section_messages
from lecturepilot.course_builder_source import course_builder_source_document
from lecturepilot.course_workspace import resolve_course_workspace
from lecturepilot.models import CourseWorkspaceSetupInput
from test_course_canvas_richness import _source_document
from test_course_canvas_section_repair import _planner, _repair_payload
from test_course_canvas_targeted_repair import _invalid_candidate
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


def test_generation_contract_writes_mixed_source_evidence_in_selected_language() -> None:
    source = _source_document(4)
    prompts = (
        planner_messages(source, output_language="de")[0]["content"],
        repair_message("bad draft", source, output_language="de")["content"],
        section_messages(source, source.sections[0], output_language="de")[0]["content"],
    )

    for prompt in prompts:
        assert "German" in prompt
        assert "evidence in any language" in prompt
        assert "formulas, code, identifiers, file paths, and source citations" in prompt


async def test_section_repair_keeps_the_selected_course_language(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planner, model = _planner(
        monkeypatch,
        [_repair_payload([{"type": "math", "text": r"w^\top x"}])],
    )
    source = published_course_canvas("targeted-repair", "lecture-01")

    await planner.repair_section(
        source,
        _invalid_candidate(source),
        section_id="learning-optimization",
        block_id="optimization-math",
        failure_context="Math block uses unsupported command \\top.",
        output_language="de",
    )

    assert "German" in model.messages[0][0]["content"]
    assert "evidence in any language" in model.messages[0][0]["content"]
