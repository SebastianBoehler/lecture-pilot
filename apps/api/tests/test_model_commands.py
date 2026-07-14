from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.model_commands import read_canvas_commands
from lecturepilot.models import (
    AgentTurnInput,
    AttendanceStatus,
    CanvasSectionPlacement,
    CanvasState,
)


def test_missing_generated_section_command_does_not_create_fake_section() -> None:
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

    assert [command.type for command in commands] == ["focus_section", "highlight_span"]


def test_example_word_without_write_request_does_not_generate_section() -> None:
    turn = _turn("Data are examples, the model predicts labels, and loss measures mistakes.")

    commands = read_canvas_commands({"message": "Good, continue.", "canvas_commands": []}, turn)

    assert [command.type for command in commands] == ["focus_section", "highlight_span"]


def test_append_word_without_section_command_does_not_create_fake_section() -> None:
    turn = _turn("no pls append a section to the cavnas")

    commands = read_canvas_commands({"message": "I added a note.", "canvas_commands": []}, turn)

    assert [command.type for command in commands] == ["focus_section", "highlight_span"]


def test_visual_request_without_section_command_does_not_create_fake_section() -> None:
    turn = _turn("new infographic, section, table, plot pls")

    commands = read_canvas_commands({"message": "I added it.", "canvas_commands": []}, turn)

    assert [command.type for command in commands] == ["focus_section", "highlight_span"]


def test_interactive_component_request_requires_explicit_component_block() -> None:
    turn = _turn("append an interactive component quiz about expected risk")

    commands = read_canvas_commands({"message": "I added it.", "canvas_commands": []}, turn)

    assert [command.type for command in commands] == ["focus_section", "highlight_span"]


def test_model_appended_section_is_not_augmented_with_synthetic_blocks() -> None:
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
    assert [block.type for block in commands[0].section.blocks] == ["paragraph"]


def test_model_appended_section_keeps_valid_placement() -> None:
    turn = _turn("append a supervised learning example")

    commands = read_canvas_commands(
        {
            "message": "Added.",
            "canvas_commands": [
                {
                    "type": "append_section",
                    "placement": {"mode": "before_section", "section_id": "supervised-learning"},
                    "section": {
                        "id": "student-supervised-example",
                        "title": "Supervised example",
                        "blocks": [{"type": "paragraph", "text": "A labeled-data example."}],
                    },
                }
            ],
        },
        turn,
    )

    assert commands[0].placement == CanvasSectionPlacement(
        mode="before_section",
        section_id="supervised-learning",
    )


def test_model_appended_section_defaults_invalid_placement_to_current_focus() -> None:
    turn = _turn("append a supervised learning example")

    commands = read_canvas_commands(
        {
            "message": "Added.",
            "canvas_commands": [
                {
                    "type": "append_section",
                    "placement": {"mode": "after_section", "section_id": "missing-section"},
                    "section": {
                        "id": "student-supervised-example",
                        "title": "Supervised example",
                        "blocks": [{"type": "paragraph", "text": "A labeled-data example."}],
                    },
                }
            ],
        },
        turn,
    )

    assert commands[0].placement == CanvasSectionPlacement(section_id="supervised-learning")


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


def test_generated_section_coerces_loose_quiz_text_to_quiz_block() -> None:
    turn = _turn("append a posterior quiz")

    commands = read_canvas_commands(
        {
            "message": "Added.",
            "canvas_commands": [
                {
                    "type": "append_section",
                    "section": {
                        "id": "posterior-choice-quiz",
                        "title": "Posterior Choice Quiz",
                        "blocks": [
                            {
                                "type": "paragraph",
                                "text": (
                                    "--- quiz\n"
                                    "text=Select the higher posterior probability.\n"
                                    "items:\n"
                                    "Posterior = 0.8\n"
                                    "Posterior = 0.2\n"
                                ),
                            }
                        ],
                    },
                }
            ],
        },
        turn,
    )

    block = commands[0].section.blocks[0]
    assert block.type == "quiz"
    assert block.text == "Select the higher posterior probability."
    assert block.items == ["Posterior = 0.8", "Posterior = 0.2"]


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
