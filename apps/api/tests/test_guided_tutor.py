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
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    harness = LecturePilotHarness()

    result = await harness.run_turn(
        AgentTurnInput(
            user_id="local-preview-user",
            course_id="martius-ml",
            lecture_id="lecture-03",
            attendance=AttendanceStatus.ABSENT,
            message="hello, I do not understand kernels yet",
            canvas_state=CanvasState(focused_section_id="feature-maps"),
        )
    )

    assert result.canvas_commands == [
        CanvasCommand(type="focus_section", section_id="skill-check")
    ]
    assert result.quality_gate is not None
    assert result.quality_gate.status == QualityGateStatus.NEEDS_EVIDENCE
    assert "answer this check" in result.message.lower()
    assert "what would you like" not in result.message.lower()


async def test_local_preview_tutor_keeps_definition_only_answer_pending(monkeypatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    harness = LecturePilotHarness()

    result = await harness.run_turn(
        AgentTurnInput(
            user_id="local-preview-user",
            course_id="martius-ml",
            lecture_id="lecture-03",
            attendance=AttendanceStatus.PRESENT,
            message="k(x, x') replaces the inner product phi(x) dot phi(x') in feature space",
            canvas_state=CanvasState(focused_section_id="skill-check"),
        )
    )

    assert result.canvas_commands[0].section_id == "skill-check"
    assert result.quality_gate is not None
    assert result.quality_gate.status == QualityGateStatus.NEEDS_EVIDENCE
    assert "gate pending" in result.message.lower()
    assert "computation" in result.message.lower()
    assert "example" in result.message.lower() or "failure" in result.message.lower()
    assert "gate passed" not in result.message.lower()


async def test_local_preview_tutor_marks_worked_kernel_answer_passed(monkeypatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    harness = LecturePilotHarness()

    result = await harness.run_turn(
        AgentTurnInput(
            user_id="local-preview-user",
            course_id="martius-ml",
            lecture_id="lecture-03",
            attendance=AttendanceStatus.PRESENT,
            message=(
                "k(x, x') replaces the inner product phi(x) dot phi(x') in feature space. "
                "That saves computation because the algorithm can avoid constructing "
                "high-dimensional lifted coordinates. For text classification this only works "
                "if the similarity matches the task; otherwise the kernel is the wrong tool."
            ),
            canvas_state=CanvasState(focused_section_id="skill-check"),
        )
    )

    assert result.canvas_commands[0].section_id == "kernel-trick"
    assert result.quality_gate is not None
    assert result.quality_gate.status == QualityGateStatus.PASSED
    assert "gate passed" in result.message.lower()


def test_model_prompt_requires_guided_quality_gate_turns() -> None:
    messages = _messages(
        AgentTurnInput(
            user_id="student01",
            course_id="martius-ml",
            lecture_id="lecture-03",
            attendance=AttendanceStatus.UNKNOWN,
            message="hello",
            canvas_state=CanvasState(focused_section_id="feature-maps"),
        )
    )

    system_prompt = messages[0]["content"].lower()
    assert "do not ask open-ended" in system_prompt
    assert "quality_gate" in system_prompt
    assert "passed" in system_prompt
    assert "needs_evidence" in system_prompt
    assert "do not mark a gate passed from keywords" in system_prompt
    assert "definition, mechanism, computation, and transfer" in system_prompt
