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


def test_append_word_triggers_student_section_fallback() -> None:
    turn = _turn("no pls append a section to the cavnas")

    commands = read_canvas_commands({"message": "I added a note.", "canvas_commands": []}, turn)

    assert commands[0].type == "append_section"
    assert commands[0].section is not None
    assert commands[0].section.title == "Generated learning note"
    assert commands[1].type == "focus_section"
    assert commands[1].section_id == commands[0].section_id


def test_new_infographic_table_plot_triggers_visual_section_fallback() -> None:
    turn = _turn("new infographic, section, table, plot pls")

    commands = read_canvas_commands({"message": "I added it.", "canvas_commands": []}, turn)

    assert commands[0].type == "append_section"
    assert commands[0].section is not None
    assert commands[0].section.title == "Generated concept infographic"
    assert "Locate" in " ".join(commands[0].section.blocks[1].items)


def test_interactive_component_request_gets_component_fallback() -> None:
    turn = _turn("append an interactive component quiz about expected risk")

    commands = read_canvas_commands({"message": "I added it.", "canvas_commands": []}, turn)

    assert commands[0].section is not None
    component = next(block for block in commands[0].section.blocks if block.type == "component")
    assert component.component_type == "single_choice_quiz"
    assert component.component_ref.endswith(".yaml")
    assert component.option_ids == ["posterior-loss", "slide-number", "notation-font"]
    assert component.answer_index == 0


def test_requested_learning_blocks_are_preserved_when_model_appends_section() -> None:
    turn = _turn("append a checkpoint quiz and table section about expected risk")
    section = CanvasSection(
        id="student-risk",
        title="Risk practice",
        blocks=[CanvasBlock(id="student-risk-p-1", type="paragraph", text="Risk practice note.")],
    )

    commands = read_canvas_commands(
        {
            "message": "Added.",
            "canvas_commands": [
                {
                    "type": "append_section",
                    "section": section.model_dump(),
                }
            ],
        },
        turn,
    )

    assert commands[0].section is not None
    assert {"checkpoint", "quiz", "table"}.issubset({block.type for block in commands[0].section.blocks})


def test_generated_component_blocks_keep_file_backed_metadata() -> None:
    turn = _turn("append an interactive risk quiz component")

    commands = read_canvas_commands(
        {
            "message": "Added.",
            "canvas_commands": [
                {
                    "type": "append_section",
                    "section": {
                        "id": "student-risk-practice",
                        "title": "Risk practice",
                        "blocks": [
                            {
                                "id": "risk-check",
                                "type": "component",
                                "component_id": "risk-threshold-check",
                                "component_type": "single_choice_quiz",
                                "version": 2,
                                "text": "Which rule should drive a cost-sensitive classifier?",
                                "options": [
                                    {
                                        "id": "lowest-risk",
                                        "text": "Choose the lowest expected risk.",
                                        "correct": True,
                                    },
                                    {
                                        "id": "highest-posterior",
                                        "text": "Always choose the highest posterior.",
                                    },
                                ],
                            }
                        ],
                    },
                }
            ],
        },
        turn,
    )

    block = commands[0].section.blocks[0]
    assert block.type == "component"
    assert block.component_id == "risk-threshold-check"
    assert block.component_type == "single_choice_quiz"
    assert block.component_ref == "risk-threshold-check.yaml"
    assert block.component_version == 2
    assert block.option_ids == ["lowest-risk", "highest-posterior"]
    assert block.answer_index == 0


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
