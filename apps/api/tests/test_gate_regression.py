from __future__ import annotations

import pytest

from lecturepilot.harness import LecturePilotHarness
from lecturepilot.models import AgentTurnInput, AttendanceStatus, CanvasState, QualityGateStatus


@pytest.mark.parametrize(
    ("lecture_id", "message", "expected_status"),
    [
        (
            "lecture-01",
            "Machine learning predicts labels from examples.",
            QualityGateStatus.NEEDS_EVIDENCE,
        ),
        (
            "lecture-01",
            "Supervised classification predicts labels from training data with a model.",
            QualityGateStatus.NEEDS_EVIDENCE,
        ),
        (
            "lecture-01",
            (
                "Supervised classification or regression predicts a target label or output from "
                "training data. A model or hypothesis is optimized with a loss/error objective, "
                "then validation or test data checks generalization instead of memorization."
            ),
            QualityGateStatus.PASSED,
        ),
        (
            "lecture-02",
            "Generalization means the model works beyond one example.",
            QualityGateStatus.NEEDS_EVIDENCE,
        ),
        (
            "lecture-02",
            "We train on training data and use validation or test data to estimate generalization.",
            QualityGateStatus.NEEDS_EVIDENCE,
        ),
        (
            "lecture-02",
            (
                "We train on the training set, use validation or held-out test data to estimate "
                "generalization and overfitting risk, and inspect classifier metrics such as false "
                "positive rate or recall because the decision threshold changes the rates."
            ),
            QualityGateStatus.PASSED,
        ),
        (
            "lecture-03",
            "The posterior is P(C|X), so Bayes updates a belief.",
            QualityGateStatus.NEEDS_EVIDENCE,
        ),
        (
            "lecture-03",
            "The posterior uses the prior, likelihood, and evidence P(X).",
            QualityGateStatus.NEEDS_EVIDENCE,
        ),
        (
            "lecture-03",
            (
                "The posterior P(C|X) combines the prior, likelihood, and evidence P(X). "
                "The classifier then chooses a decision, and loss or false-positive cost can "
                "move the risk-sensitive threshold."
            ),
            QualityGateStatus.PASSED,
        ),
    ],
)
async def test_learning_gate_regression_matrix(
    monkeypatch: pytest.MonkeyPatch,
    lecture_id: str,
    message: str,
    expected_status: QualityGateStatus,
) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    result = await LecturePilotHarness().run_turn(
        AgentTurnInput(
            user_id="local-preview-user",
            course_id="martius-ml",
            lecture_id=lecture_id,
            attendance=AttendanceStatus.PRESENT,
            message=message,
            canvas_state=CanvasState(focused_section_id=None),
        )
    )

    assert result.quality_gate is not None
    assert result.quality_gate.status == expected_status
    assert result.canvas_commands[0].type == "focus_section"
    assert result.canvas_commands[1].type == "highlight_span"
    if expected_status == QualityGateStatus.NEEDS_EVIDENCE:
        assert result.quality_gate.next_prompt
        assert result.quality_gate.next_prompt.startswith("Add one concrete sentence for:")
        assert "gate pending" in result.message.lower()
    else:
        assert "gate passed" in result.message.lower()


@pytest.mark.parametrize(
    ("attendance", "expected_phrase"),
    [
        (AttendanceStatus.PRESENT, "verification mode"),
        (AttendanceStatus.ABSENT, "guided walkthrough mode"),
    ],
)
async def test_gate_regression_preserves_attendance_mode(
    monkeypatch: pytest.MonkeyPatch,
    attendance: AttendanceStatus,
    expected_phrase: str,
) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    result = await LecturePilotHarness().run_turn(
        AgentTurnInput(
            user_id="local-preview-user",
            course_id="martius-ml",
            lecture_id="lecture-02",
            attendance=attendance,
            message="I only remember that generalization is important.",
            canvas_state=CanvasState(focused_section_id=None),
        )
    )

    assert result.quality_gate is not None
    assert result.quality_gate.status == QualityGateStatus.NEEDS_EVIDENCE
    assert expected_phrase in result.message.lower()
