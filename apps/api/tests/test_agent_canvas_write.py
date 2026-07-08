from __future__ import annotations

from canvas_workspace_fixtures import write_course_source
from lecturepilot.agent_canvas_write import normalize_student_canvas_markdown
from lecturepilot.agent_tool_executor import AgentToolExecutor
from lecturepilot.canvas_workspace import CanvasWorkspace


def test_student_canvas_write_normalizes_model_quiz_lines() -> None:
    markdown = normalize_student_canvas_markdown(
        "/lecture/canvas/student/posterior-higher-quiz.md",
        (
            "section_id=posterior-higher-quiz; title=Choosing Higher Posterior Quiz\n"
            "span_id=posterior-higher-quiz-1; type=quiz; "
            "text=Which class has the higher posterior?; items=[\"C1\", \"C2\"]\n"
        ),
    )

    assert 'title: "Choosing Higher Posterior Quiz"' in markdown
    assert 'type="quiz"' in markdown
    assert ":::quiz" in markdown
    assert "Which class has the higher posterior?" in markdown
    assert "- C1" in markdown
    assert "section_id=" not in markdown


def test_student_canvas_write_normalizes_yamlish_quiz_blocks() -> None:
    markdown = normalize_student_canvas_markdown(
        "/lecture/canvas/student/higher-posterior-quiz.md",
        (
            "# Higher Posterior Quiz\n"
            "quiz:\n"
            'text: "Which class has the higher posterior?"\n'
            "items:\n"
            "- id: a\n"
            'text: "Class A with posterior 0.7"\n'
            "correct: true\n"
            "- id: b\n"
            'text: "Class B with posterior 0.3"\n'
            "correct: false\n"
        ),
    )

    assert 'type="quiz"' in markdown
    assert "Which class has the higher posterior?" in markdown
    assert "- [x] Class A with posterior 0.7" in markdown
    assert "- Class B with posterior 0.3" in markdown
    assert "quiz:" not in markdown


def test_student_canvas_write_normalizes_line_schema_quiz_blocks() -> None:
    markdown = normalize_student_canvas_markdown(
        "/lecture/canvas/student/final-tiny-quiz.md",
        (
            "section_id=final-tiny-quiz\n"
            "title=Final Tiny Quiz\n"
            "span_id=final-tiny-quiz-1\n"
            "type=quiz\n"
            "text=Choose class A if posterior is 0.8 or class B if posterior is 0.2.\n"
            "items:\n"
            "id=opt1\n"
            "text=Class A\n"
            "correct=true\n"
            "id=opt2\n"
            "text=Class B\n"
            "correct=false\n"
        ),
    )

    assert 'title: "Final Tiny Quiz"' in markdown
    assert 'block id="final-tiny-quiz-1" type="quiz"' in markdown
    assert "- [x] Class A" in markdown
    assert "- Class B" in markdown
    assert "section_id=" not in markdown


def test_student_canvas_write_normalizes_indented_yaml_quiz_blocks() -> None:
    markdown = normalize_student_canvas_markdown(
        "/lecture/canvas/student/decision-making-under-uncertainty-quiz.md",
        (
            "# Decision Making Under Uncertainty Quiz\n"
            "Tiny Quiz\n"
            'text: "Which class has the higher posterior probability?"\n'
            "items:\n"
            "- id: a\n"
            '  text: "Class A"\n'
            "  correct: true\n"
            "- id: b\n"
            '  text: "Class B"\n'
            "  correct: false\n"
        ),
    )

    assert 'type="quiz"' in markdown
    assert "Which class has the higher posterior probability?" in markdown
    assert "- [x] Class A" in markdown
    assert "- Class B" in markdown
    assert "Tiny Quiz" not in markdown


def test_student_canvas_write_normalizes_loose_quiz_blocks() -> None:
    markdown = normalize_student_canvas_markdown(
        "/lecture/canvas/student/posterior-choice-quiz.md",
        (
            "# Posterior Choice Quiz\n"
            "--- section\n"
            "id=posterior-choice-quiz\n"
            "title=Posterior Choice Quiz\n"
            "--- quiz\n"
            "text=Select the higher posterior probability.\n"
            "items:\n"
            "Posterior = 0.8\n"
            "Posterior = 0.2\n"
        ),
    )

    assert 'type="quiz"' in markdown
    assert "Select the higher posterior probability." in markdown
    assert "- Posterior = 0.8" in markdown
    assert "- Posterior = 0.2" in markdown
    assert "--- quiz" not in markdown


def test_ordered_student_path_does_not_leak_into_section_id(tmp_path) -> None:
    workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=write_course_source(tmp_path),
    )
    workspace.read_document(course_id="martius-ml", lecture_id="lecture-03", user_id="u1")
    executor = AgentToolExecutor(
        canvas_workspace=workspace,
        course_id="martius-ml",
        lecture_id="lecture-03",
        user_id="u1",
    )
    first = executor.execute(
        "write",
        {
            "path": "/lecture/canvas/student/prior-explanation.md",
            "content": "# Prior Explanation\n\nA prior is the baseline belief before evidence.",
        },
    )

    assert first["ok"] is True
    assert first["path"] == "/lecture/canvas/student/90-prior-explanation.md"
    assert first["section_id"] == "prior-explanation-md"

    second = executor.execute(
        "write",
        {
            "path": first["path"],
            "content": "# Prior Explanation\n\nUpdated with a sharper example.",
        },
    )

    assert second["ok"] is True
    assert second["section_id"] == "prior-explanation-md"
    document = workspace.read_document(course_id="martius-ml", lecture_id="lecture-03", user_id="u1")
    section = document.sections[-1]
    assert section.id == "prior-explanation-md"
    assert section.title == "Prior Explanation"
