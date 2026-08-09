from lecturepilot.learning_map import LearningMapGate
from lecturepilot.model_commands import read_quality_gate
from lecturepilot.models import AgentTurnInput, AttendanceStatus, QualityGateStatus


def _turn(gate: LearningMapGate | None = None) -> AgentTurnInput:
    return AgentTurnInput(
        user_id="student-1",
        course_id="course-1",
        lecture_id="lecture-14",
        attendance=AttendanceStatus.PRESENT,
        message="My explanation.",
        active_gate=gate,
    )


def _gate() -> LearningMapGate:
    return LearningMapGate(
        id="causal-transfer-check",
        concept_id="causal-transfer",
        title="Causal transfer",
        prompt="Explain when the conclusion transfers.",
        evidence_criteria=[
            {"id": "mechanism", "description": "Explain the causal mechanism."},
            {"id": "boundary", "description": "Name a transfer boundary."},
        ],
        transfer_prompt="Apply this to an unfamiliar hospital setting.",
        section_id="causal-transfer",
    )


def test_quality_gate_preserves_selected_contract_id() -> None:
    gate = _gate()
    decision = read_quality_gate(
        {
            "quality_gate": {
                "gate_id": "invented-id",
                "status": "needs_evidence",
                "reason": "A boundary is missing.",
                "evidence_ids": ["mechanism"],
                "missing_evidence_ids": ["boundary"],
            }
        },
        _turn(gate),
    )

    assert decision is not None
    assert decision.gate_id == "causal-transfer-check"
    assert decision.gate_revision == gate.revision


def test_quality_gate_filters_unknown_evidence_ids() -> None:
    decision = read_quality_gate(
        {
            "quality_gate": {
                "gate_id": "causal-transfer-check",
                "status": "needs_evidence",
                "reason": "A boundary is missing.",
                "evidence_ids": ["mechanism", "invented-evidence"],
                "missing_evidence_ids": ["boundary", "another-invention"],
            }
        },
        _turn(_gate()),
    )

    assert decision is not None
    assert decision.evidence_ids == ["mechanism"]
    assert decision.missing_evidence_ids == ["boundary"]


def test_quality_gate_pass_without_required_evidence_fails_closed() -> None:
    decision = read_quality_gate(
        {
            "quality_gate": {
                "gate_id": "causal-transfer-check",
                "status": "passed",
                "reason": "The answer looks plausible.",
                "evidence_ids": ["mechanism"],
                "missing_evidence_ids": [],
            }
        },
        _turn(_gate()),
    )

    assert decision is not None
    assert decision.status == QualityGateStatus.NEEDS_EVIDENCE
    assert decision.missing_evidence_ids == ["boundary"]


def test_quality_gate_is_absent_without_active_contract() -> None:
    decision = read_quality_gate(
        {
            "quality_gate": {
                "gate_id": "invented-id",
                "status": "passed",
                "reason": "Invented generic mastery.",
            }
        },
        _turn(),
    )

    assert decision is None
