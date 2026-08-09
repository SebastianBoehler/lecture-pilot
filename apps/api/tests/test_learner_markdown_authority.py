import json
from pathlib import Path

from auth_helpers import student_headers
from lecturepilot.canvas_models import CanvasBlock, CanvasSection
from lecturepilot.models import CanvasSectionPlacement
from test_quiz_learner_overlay import COURSE_ID, LECTURE_ID, _client, _submit


def test_learner_component_and_placement_are_self_contained_in_markdown(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    workspace = client.app.state.canvas_workspace
    section = CanvasSection(
        id="student-inline-component",
        title="Inline learner component",
        source_ref="student workspace",
        blocks=[
            CanvasBlock(
                id="inline-component-block",
                type="component",
                component_id="inline-quiz",
                component_type="single_choice_quiz",
                component_ref="inline-quiz.yaml",
                component_version=2,
                caption="Inline quiz",
                text="Which answer is grounded?",
                items=["External mutation", "Markdown snapshot"],
                option_ids=["external", "markdown"],
                answer_index=1,
            )
        ],
    )
    workspace.apply_sections(
        course_id=COURSE_ID,
        lecture_id=LECTURE_ID,
        user_id="student-a",
        sections=[section],
        placements={section.id: CanvasSectionPlacement(mode="before_section", section_id="risk")},
    )
    canvas_dir = workspace.layout.user_canvas_dir("student-a", COURSE_ID, LECTURE_ID)
    markdown_path = next((canvas_dir / "student").glob("*.md"))
    markdown_before = markdown_path.read_bytes()
    headers = student_headers("student-a", course_ids=[COURSE_ID])

    initial = client.get(f"/courses/{COURSE_ID}/lectures/{LECTURE_ID}/canvas", headers=headers)
    initial_answer = _submit(client, headers, "inline-attempt", "inline-quiz", 1)
    components = canvas_dir / "components"
    components.mkdir(exist_ok=True)
    (components / "inline-quiz.yaml").write_text(
        "id: inline-quiz\ntype: single_choice_quiz\nprompt: Mutated\noptions:\n"
        "  - text: External mutation\n    correct: true\n",
        encoding="utf-8",
    )
    (canvas_dir / "placement.json").write_text(
        json.dumps({section.id: {"mode": "after_section", "section_id": "risk"}}),
        encoding="utf-8",
    )

    after = client.get(f"/courses/{COURSE_ID}/lectures/{LECTURE_ID}/canvas", headers=headers)
    replay = _submit(client, headers, "inline-attempt-2", "inline-quiz", 1)

    assert initial.status_code == after.status_code == 200
    assert initial.json()["document"] == after.json()["document"]
    assert [item["id"] for item in after.json()["document"]["sections"]][:2] == [
        section.id,
        "risk",
    ]
    assert initial_answer.json()["correct"] is replay.json()["correct"] is True
    assert markdown_path.read_bytes() == markdown_before
    markdown_text = markdown_before.decode()
    assert 'placement_mode: "before_section"' in markdown_text
    assert '"type": "single_choice_quiz"' in markdown_text


def test_learner_markdown_rejects_external_component_references(tmp_path: Path) -> None:
    client = _client(tmp_path)
    workspace = client.app.state.canvas_workspace
    canvas_dir = workspace.layout.user_canvas_dir("student-a", COURSE_ID, LECTURE_ID)
    student_dir = canvas_dir / "student"
    student_dir.mkdir(parents=True)
    (student_dir / "90-external.md").write_text(
        """---
id: "student-external"
title: "External"
source_ref: "student workspace"
---

<!-- block id="external-component" type="component" -->
:::component external.yaml
:::
""",
        encoding="utf-8",
    )
    components = canvas_dir / "components"
    components.mkdir()
    (components / "external.yaml").write_text(
        "id: external\ntype: single_choice_quiz\n",
        encoding="utf-8",
    )

    response = client.get(
        f"/courses/{COURSE_ID}/lectures/{LECTURE_ID}/canvas",
        headers=student_headers("student-a", course_ids=[COURSE_ID]),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Learner component blocks must contain their complete payload in Markdown."
    )
