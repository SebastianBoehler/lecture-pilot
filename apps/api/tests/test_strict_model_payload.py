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
            "reason": "The boundary is missing.",
            "evidence_ids": ["causal-link"],
        },
        "next_check": {
            "gate_id": gate.id,
            "gate_revision": gate.revision,
            "prompt": "Explain the mechanism.",
            "assistance": {"level": "cue", "content": "Use the causal link."},
        },
    }


def _append_section_command() -> dict:
    return {
        "type": "append_section",
        "section_id": "generated-example",
        "span_id": None,
        "highlight_text": None,
        "artifact_id": None,
        "section": {
            "id": "generated-example",
            "title": "Generated example",
            "source_ref": "student workspace",
            "blocks": [
                {
                    "id": "generated-example-text",
                    "type": "paragraph",
                    "text": "A changed example.",
                    "items": [],
                    "asset_path": None,
                    "asset_url": None,
                    "caption": None,
                    "answer_index": None,
                    "component_id": None,
                    "component_type": None,
                    "component_ref": None,
                    "component_version": None,
                    "option_ids": [],
                    "component_data": None,
                }
            ],
        },
        "placement": {"mode": "after_section", "section_id": "mechanism"},
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


def test_provider_payload_rejects_non_provider_section_fields() -> None:
    payload = _payload()
    command = _append_section_command()
    command["section"]["practice_exam_eligible"] = False
    payload["canvas_commands"].append(command)

    with pytest.raises(ProviderConfigurationError):
        _parse(payload)


def test_provider_payload_rejects_unknown_nested_block_fields() -> None:
    payload = _payload()
    command = _append_section_command()
    command["section"]["blocks"][0]["unexpected"] = "discarded today"
    payload["canvas_commands"].append(command)

    with pytest.raises(ProviderConfigurationError):
        _parse(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("gate_id", "invented-gate"),
        ("gate_revision", "f" * 64),
        ("evidence_ids", ["invented-evidence"]),
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


def test_provider_payload_derives_the_gate_outcome_from_evidence() -> None:
    payload = _payload()

    result = _parse(payload)

    assert result.quality_gate.status.value == "needs_evidence"
    assert result.quality_gate.missing_evidence_ids == ["boundary"]


def test_provider_payload_resolves_highlight_section_from_the_block() -> None:
    turn = _turn().model_copy(deep=True)
    turn.canvas_context.sections.append(
        CanvasSection(
            id="application",
            title="Application",
            blocks=[CanvasBlock(id="application-text", type="paragraph", text="Apply it here.")],
        )
    )
    payload = _payload()
    payload["canvas_commands"][1]["span_id"] = "application-text"

    result = agent_result_from_content(json.dumps(payload), turn, "model")

    assert result.canvas_commands[1].section_id == "application"


def test_provider_schema_requires_gate_revision() -> None:
    schema = lecturepilot_response_format(_turn())["json_schema"]["schema"]
    gate_schema = schema["properties"]["assessment"]

    assert "gate_revision" in gate_schema["properties"]
    assert "gate_revision" in gate_schema["required"]
    assert gate_schema["properties"]["gate_id"] == {"type": "string", "const": _gate().id}
    assert gate_schema["properties"]["gate_revision"] == {
        "type": "string",
        "const": _gate().revision,
    }
