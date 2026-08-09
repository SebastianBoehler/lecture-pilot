import json

import pytest

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.learning_map import LearningMapGate
from lecturepilot.agent_response_schema import lecturepilot_response_format
from lecturepilot.model_payload import agent_result_from_content
from lecturepilot.models import AgentCoachingContext, AgentTurnInput, AttendanceStatus
from lecturepilot.providers import ProviderConfigurationError


def _gate() -> LearningMapGate:
    return LearningMapGate.create(
        id="mechanism-check",
        concept_id="mechanism",
        title="Mechanism check",
        prompt="Explain the mechanism.",
        evidence_criteria=[
            {"id": "causal-link", "description": "Names the cause and its effect."},
            {"id": "boundary", "description": "Names one boundary."},
        ],
        transfer_prompt="Apply the mechanism to a changed case.",
        review_after_days=2,
        section_id="mechanism",
        source_ref="lecture.md#mechanism",
    )


def _turn(*, active_gate: bool = True, bound_check: bool = True) -> AgentTurnInput:
    gate = _gate() if active_gate else None
    return AgentTurnInput(
        user_id="student-1",
        course_id="course-1",
        lecture_id="lecture-1",
        attendance=AttendanceStatus.PRESENT,
        message="My explanation.",
        active_gate=gate,
        coaching_context=(
            AgentCoachingContext(
                active_gate_id=gate.id,
                active_gate_revision=gate.revision,
                pending_check_gate_id=gate.id,
                pending_check_gate_revision=gate.revision,
                pending_check_issued_at="2026-08-09T08:00:00+00:00",
                pending_check_prompt="Explain the mechanism.",
            )
            if gate is not None and bound_check
            else AgentCoachingContext(
                active_gate_id=(gate.id if gate else None),
                active_gate_revision=(gate.revision if gate else None),
            )
        ),
        canvas_context=CanvasDocument(
            id="course-1-lecture-1",
            course_id="course-1",
            lecture_id="lecture-1",
            title="Lecture",
            source_kind="generated",
            source_ref="lecture.md",
            workspace_path="course/index.md",
            sections=[
                CanvasSection(
                    id="mechanism",
                    title="Mechanism",
                    blocks=[
                        CanvasBlock(
                            id="mechanism-text",
                            type="paragraph",
                            text="The cause produces the effect under a boundary.",
                        )
                    ],
                )
            ],
        ),
    )


def _payload() -> dict:
    gate = _gate()
    return {
        "message": "Use the causal link. Explain the mechanism.",
        "session_goal": "Explain and transfer the mechanism.",
        "canvas_commands": [
            {
                "type": "focus_section",
                "section_id": "mechanism",
                "span_id": None,
                "highlight_text": None,
                "artifact_id": None,
                "section": None,
                "placement": None,
            },
            {
                "type": "highlight_span",
                "section_id": "mechanism",
                "span_id": "mechanism-text",
                "highlight_text": "cause produces the effect",
                "artifact_id": None,
                "section": None,
                "placement": None,
            },
        ],
        "assessment": {
            "gate_id": gate.id,
            "gate_revision": gate.revision,
            "status": "needs_evidence",
            "reason": "The boundary is missing.",
            "evidence_ids": ["causal-link"],
            "missing_evidence_ids": ["boundary"],
        },
        "next_check": {
            "gate_id": gate.id,
            "gate_revision": gate.revision,
            "prompt": "Explain the mechanism.",
            "assistance": {"level": "cue", "content": "Use the causal link."},
        },
    }


def _parse(payload: dict, *, active_gate: bool = True):
    return agent_result_from_content(json.dumps(payload), _turn(active_gate=active_gate), "model")


@pytest.mark.parametrize("missing", ["session_goal", "assessment", "next_check"])
def test_provider_payload_rejects_missing_required_fields(missing: str) -> None:
    payload = _payload()
    payload.pop(missing)

    with pytest.raises(ProviderConfigurationError):
        _parse(payload)


def test_provider_payload_rejects_extra_fields_and_code_fences() -> None:
    payload = _payload()
    payload["unexpected"] = "not part of the contract"
    with pytest.raises(ProviderConfigurationError):
        _parse(payload)

    fenced = f"```json\n{json.dumps(_payload())}\n```"
    with pytest.raises(ProviderConfigurationError):
        agent_result_from_content(fenced, _turn(), "model")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("gate_id", "invented-gate"),
        ("gate_revision", "f" * 64),
        ("evidence_ids", ["invented-evidence"]),
        ("missing_evidence_ids", ["invented-evidence"]),
    ],
)
def test_provider_payload_rejects_gate_contract_mismatches(field: str, value: object) -> None:
    payload = _payload()
    payload["assessment"][field] = value

    with pytest.raises(ProviderConfigurationError):
        _parse(payload)


def test_provider_payload_rejects_missing_required_canvas_commands() -> None:
    payload = _payload()
    payload["canvas_commands"] = []

    with pytest.raises(ProviderConfigurationError):
        _parse(payload)


def test_provider_payload_rejects_gate_decision_without_active_gate() -> None:
    with pytest.raises(ProviderConfigurationError):
        _parse(_payload(), active_gate=False)


def test_provider_payload_rejects_assessment_without_bound_check() -> None:
    with pytest.raises(ProviderConfigurationError):
        agent_result_from_content(json.dumps(_payload()), _turn(bound_check=False), "model")


def test_provider_payload_accepts_unbound_turn_without_assessment() -> None:
    payload = _payload()
    payload["assessment"] = None

    result = agent_result_from_content(json.dumps(payload), _turn(bound_check=False), "model")

    assert result.quality_gate is None
    assert result.next_check is not None


def test_provider_payload_accepts_one_complete_strict_contract() -> None:
    result = _parse(_payload())

    assert result.quality_gate is not None
    assert result.quality_gate.gate_revision == _gate().revision
    assert [command.type for command in result.canvas_commands] == [
        "focus_section",
        "highlight_span",
    ]


def test_provider_schema_requires_gate_revision() -> None:
    schema = lecturepilot_response_format()["json_schema"]["schema"]
    gate_schema = schema["properties"]["assessment"]

    assert "gate_revision" in gate_schema["properties"]
    assert "gate_revision" in gate_schema["required"]
