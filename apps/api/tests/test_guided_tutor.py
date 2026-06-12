from lecturepilot.harness import LecturePilotHarness
from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.model_client import _messages
from lecturepilot.model_commands import read_canvas_commands
from lecturepilot.models import (
    AgentTurnInput,
    AttendanceStatus,
    CanvasCommand,
    CanvasState,
    QualityGateStatus,
)


async def test_local_preview_tutor_runs_without_provider_key(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    harness = LecturePilotHarness()

    result = await harness.run_turn(
        AgentTurnInput(
            user_id="local-preview-user",
            course_id="martius-ml",
            lecture_id="lecture-03",
            attendance=AttendanceStatus.ABSENT,
            message="hello, I do not understand Bayes yet",
            canvas_state=CanvasState(focused_section_id="bayesian-decision-theory-the-aim"),
        )
    )

    assert result.canvas_commands[0] == CanvasCommand(
        type="focus_section",
        section_id="bayesian-decision-theory-the-aim",
    )
    assert result.canvas_commands[1].type == "highlight_span"
    assert result.quality_gate is not None
    assert result.quality_gate.status == QualityGateStatus.NEEDS_EVIDENCE
    assert "guided walkthrough mode" in result.message.lower()
    assert "step" in result.message.lower()
    assert "gate pending" in result.message.lower()
    assert "what would you like" not in result.message.lower()


async def test_local_preview_tutor_keeps_definition_only_answer_pending(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    harness = LecturePilotHarness()

    result = await harness.run_turn(
        AgentTurnInput(
            user_id="local-preview-user",
            course_id="martius-ml",
            lecture_id="lecture-03",
            attendance=AttendanceStatus.PRESENT,
            message="The posterior is P(C|X), so Bayes updates a belief.",
            canvas_state=CanvasState(focused_section_id="bayes-formula"),
        )
    )

    assert result.canvas_commands[0].section_id == "bayes-formula"
    assert result.canvas_commands[1].highlight_text == "probability"
    assert result.quality_gate is not None
    assert result.quality_gate.status == QualityGateStatus.NEEDS_EVIDENCE
    assert "verification mode" in result.message.lower()
    assert "feedback" in result.message.lower()
    assert "gate pending" in result.message.lower()
    assert "risk or cost" in result.message.lower()
    assert "gate passed" not in result.message.lower()


async def test_local_preview_tutor_marks_worked_bayes_answer_passed(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    harness = LecturePilotHarness()

    result = await harness.run_turn(
        AgentTurnInput(
            user_id="local-preview-user",
            course_id="martius-ml",
            lecture_id="lecture-03",
            attendance=AttendanceStatus.PRESENT,
            message=(
                "The posterior P(C|X) is computed from the prior, likelihood, and evidence P(X). "
                "Then the classifier chooses the class or action with the best expected decision. "
                "If a false positive has high cost, the risk changes the final choice."
            ),
            canvas_state=CanvasState(focused_section_id="bayes-formula"),
        )
    )

    assert result.canvas_commands[0].section_id == "losses-and-risks"
    assert result.quality_gate is not None
    assert result.quality_gate.status == QualityGateStatus.PASSED
    assert "gate passed" in result.message.lower()


async def test_local_preview_tutor_appends_personalized_canvas_section(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    harness = LecturePilotHarness()

    result = await harness.run_turn(
        AgentTurnInput(
            user_id="local-preview-user",
            course_id="martius-ml",
            lecture_id="lecture-03",
            attendance=AttendanceStatus.ABSENT,
            message="Explain this with a soccer example.",
            canvas_state=CanvasState(focused_section_id="bayes-formula"),
        )
    )

    section_command = result.canvas_commands[0]
    assert section_command.type == "append_section"
    assert section_command.section is not None
    assert section_command.section.id == "student-soccer-bayes-example"
    assert result.canvas_commands[1].section_id == "student-soccer-bayes-example"
    assert result.quality_gate is not None
    assert result.quality_gate.status == QualityGateStatus.NEEDS_EVIDENCE


async def test_local_preview_tutor_routes_risk_questions_to_risk_section(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    harness = LecturePilotHarness()

    result = await harness.run_turn(
        AgentTurnInput(
            user_id="local-preview-user",
            course_id="martius-ml",
            lecture_id="lecture-03",
            attendance=AttendanceStatus.ABSENT,
            message="False positives and false negatives have different costs, so risk changes the threshold.",
            canvas_state=CanvasState(focused_section_id="bayes-formula"),
        )
    )

    assert result.canvas_commands[0] == CanvasCommand(
        type="focus_section",
        section_id="losses-and-risks",
    )
    assert result.canvas_commands[1].section_id == "losses-and-risks"
    assert result.canvas_commands[1].span_id == "losses-and-risks-list"
    assert result.canvas_commands[1].highlight_text == "costly"


def test_model_prompt_requires_guided_quality_gate_turns() -> None:
    messages = _messages(
        AgentTurnInput(
            user_id="student01",
            course_id="martius-ml",
            lecture_id="lecture-03",
            attendance=AttendanceStatus.UNKNOWN,
            message="hello",
            canvas_state=CanvasState(focused_section_id="bayes-formula"),
        )
    )

    system_prompt = messages[0]["content"].lower()
    assert "do not ask open-ended" in system_prompt
    assert "quality_gate" in system_prompt
    assert "passed" in system_prompt
    assert "needs_evidence" in system_prompt
    assert "do not mark a gate passed from keywords" in system_prompt
    assert "definition, mechanism, computation, and transfer" in system_prompt
    assert "attendance selects the tutor stance" in system_prompt
    assert "examiner and coach" in system_prompt
    assert "teacher for an absent student" in system_prompt
    assert "canvas_commands" in system_prompt
    assert "highlight_span" in system_prompt


def test_model_prompt_includes_canvas_targets() -> None:
    messages = _messages(_contextual_turn())

    user_prompt = messages[1]["content"]
    assert "Canvas title: Bayesian Decision Theory" in user_prompt
    assert "Active quality gate: bayes-decision-check" in user_prompt
    assert "posterior from evidence" in user_prompt
    assert "section_id=bayes-formula" in user_prompt
    assert "span_id=bayes-formula-list" in user_prompt
    assert "Posterior" in user_prompt


def test_model_parser_accepts_focus_and_highlight_commands() -> None:
    commands = read_canvas_commands(
        {
            "canvas_commands": [
                {"type": "focus_section", "section_id": "bayes-formula"},
                {
                    "type": "highlight_span",
                    "section_id": "wrong-section",
                    "span_id": "bayes-formula-list",
                    "highlight_text": "Posterior",
                },
            ]
        },
        _contextual_turn(),
    )

    assert commands == [
        CanvasCommand(type="focus_section", section_id="bayes-formula"),
        CanvasCommand(
            type="highlight_span",
            section_id="bayes-formula",
            span_id="bayes-formula-list",
            highlight_text="Posterior",
        ),
    ]


def test_model_parser_rejects_invalid_canvas_ids() -> None:
    commands = read_canvas_commands(
        {
            "canvas_commands": [
                {"type": "focus_section", "section_id": "not-in-canvas"},
                {"type": "highlight_span", "section_id": "bayes-formula", "span_id": "missing-block"},
            ]
        },
        _contextual_turn(),
    )

    assert commands == [
        CanvasCommand(type="focus_section", section_id="bayes-formula"),
        CanvasCommand(
            type="highlight_span",
            section_id="bayes-formula",
            span_id="bayes-formula-list",
            highlight_text="Prior",
        ),
    ]


def test_model_parser_accepts_generated_student_section() -> None:
    commands = read_canvas_commands(
        {
            "canvas_commands": [
                {
                    "type": "append_section",
                    "section": {
                        "id": "soccer-risk-infographic",
                        "title": "Soccer risk infographic",
                        "blocks": [
                            {
                                "type": "callout",
                                "text": "A scouting report is evidence; the signing decision depends on risk.",
                            },
                            {
                                "type": "list",
                                "items": ["Prior player fit", "Likelihood of report", "Posterior belief"],
                            },
                        ],
                    },
                }
            ]
        },
        _contextual_turn(),
    )

    assert commands[0].type == "append_section"
    assert commands[0].section is not None
    assert commands[0].section.id.startswith("student-soccer-risk-infographic")
    assert commands[0].section.source_ref == "student workspace"
    assert commands[1].type == "focus_section"


def _contextual_turn() -> AgentTurnInput:
    return AgentTurnInput(
        user_id="student01",
        course_id="martius-ml",
        lecture_id="lecture-03",
        attendance=AttendanceStatus.UNKNOWN,
        message="hello",
        canvas_state=CanvasState(focused_section_id="bayes-formula"),
        canvas_context=CanvasDocument(
            id="martius-ml-lecture-03",
            course_id="martius-ml",
            lecture_id="lecture-03",
            title="Bayesian Decision Theory",
            source_kind="latex",
            source_ref="Lecture03-eng.tex",
            workspace_path=".lecturepilot/workspaces/test/canvas/index.md",
            sections=[
                CanvasSection(
                    id="bayes-formula",
                    title="Bayes formula and conditional probability",
                    blocks=[
                        CanvasBlock(
                            id="bayes-formula-list",
                            type="list",
                            items=["Prior", "Likelihood", "Evidence", "Posterior"],
                        )
                    ],
                )
            ],
        ),
    )
