from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.model_commands import read_canvas_commands
from lecturepilot.models import AgentTurnInput, AttendanceStatus, CanvasState


def test_missing_generated_section_tool_gets_student_workspace_fallback() -> None:
    turn = AgentTurnInput(
        user_id="student01",
        course_id="martius-ml",
        lecture_id="lecture-03",
        attendance=AttendanceStatus.ABSENT,
        message="Add a soccer example note to the canvas for Bayes.",
        canvas_state=CanvasState(focused_section_id="bayes-formula"),
        canvas_context=CanvasDocument(
            id="doc",
            course_id="martius-ml",
            lecture_id="lecture-03",
            title="Bayesian Decision Theory",
            source_kind="latex",
            source_ref="Lecture03-eng.tex",
            workspace_path=".lecturepilot/workspaces/demo/canvas/index.md",
            sections=[
                CanvasSection(
                    id="bayes-formula",
                    title="Bayes formula and conditional probability",
                    blocks=[
                        CanvasBlock(
                            id="bayes-formula-p-1",
                            type="paragraph",
                            text="Bayes rule maps evidence to a posterior.",
                        )
                    ],
                )
            ],
        ),
    )

    commands = read_canvas_commands({"message": "I added it.", "canvas_commands": []}, turn)

    assert commands[0].type == "append_section"
    assert commands[0].section is not None
    assert commands[0].section.title == "Soccer scouting example"
    assert commands[0].section.source_ref == "student workspace"
    assert commands[1].type == "focus_section"
    assert commands[1].section_id == commands[0].section_id


def test_example_word_without_write_request_does_not_generate_section() -> None:
    turn = _turn("Data are examples, the model predicts labels, and loss measures mistakes.")

    commands = read_canvas_commands({"message": "Good, continue.", "canvas_commands": []}, turn)

    assert [command.type for command in commands] == ["focus_section", "highlight_span"]


def _turn(message: str) -> AgentTurnInput:
    return AgentTurnInput(
        user_id="student01",
        course_id="martius-ml",
        lecture_id="lecture-01",
        attendance=AttendanceStatus.PRESENT,
        message=message,
        canvas_state=CanvasState(focused_section_id="supervised-learning"),
        canvas_context=CanvasDocument(
            id="doc",
            course_id="martius-ml",
            lecture_id="lecture-01",
            title="Introduction",
            source_kind="latex",
            source_ref="Lecture01-eng.tex",
            workspace_path=".lecturepilot/workspaces/demo/canvas/index.md",
            sections=[
                CanvasSection(
                    id="supervised-learning",
                    title="Supervised learning",
                    blocks=[
                        CanvasBlock(
                            id="supervised-learning-p-1",
                            type="paragraph",
                            text="Learning uses data, model, loss, and optimization.",
                        )
                    ],
                )
            ],
        ),
    )
