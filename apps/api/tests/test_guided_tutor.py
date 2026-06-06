from lecturepilot.harness import LecturePilotHarness
from lecturepilot.model_client import _messages
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

    assert result.canvas_commands[0].section_id == "bayesian-decision-theory-the-aim"
    assert result.quality_gate is not None
    assert result.quality_gate.status == QualityGateStatus.NEEDS_EVIDENCE
    assert "verification mode" in result.message.lower()
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

    assert result.canvas_commands[0].section_id == "bayes-rule-to-sum-up"
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
