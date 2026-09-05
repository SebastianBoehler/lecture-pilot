import json

import pytest

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.learning_map import LearningMapGate
from lecturepilot.model_payload import agent_result_from_content
from lecturepilot.models import AgentCoachingContext, AgentTurnInput, AttendanceStatus
from lecturepilot.providers import ProviderConfigurationError
from practice_gate_coaching_test_helpers import practice_gate


@pytest.mark.parametrize(
    ("prompt", "level", "content"),
    [
        (
            "Apply the boundary to a parallel case without help.",
            "prompt",
            "Name the invariant first.",
        ),
        (
            "Diagnose the mechanism in the canonical case.",
            "cue",
            "Check the changed surface against the invariant.",
        ),
        ("Diagnose the mechanism in the canonical case.", "prompt", "Invented model hint."),
    ],
)
def test_provider_cannot_substitute_the_server_selected_failed_diagnostic_check(
    prompt: str,
    level: str,
    content: str,
) -> None:
    gate = practice_gate()
    payload = _payload(
        gate,
        evidence_ids=[],
        next_prompt=prompt,
        assistance_level=level,
        assistance_content=content,
    )

    payload["next_check"] = {
        "prompt": prompt,
        "assistance": {"level": level, "content": content},
    }
    with pytest.raises(ProviderConfigurationError, match="result contract"):
        _parse(gate, payload, stage="diagnostic")


def test_server_issues_exact_independent_exit_after_diagnostic_pass() -> None:
    gate = practice_gate()
    payload = _payload(
        gate,
        evidence_ids=["boundary"],
        next_prompt=gate.prompt,
        assistance_level="none",
        assistance_content=None,
    )

    result = _parse(gate, payload, stage="diagnostic")
    assert result.next_check.prompt == gate.independent_exit_task
    assert result.next_check.assistance.level == "none"


def test_provider_accepts_exact_approved_hint_and_prompt() -> None:
    gate = practice_gate()
    payload = _payload(
        gate,
        evidence_ids=[],
        next_prompt=gate.prompt,
        assistance_level="prompt",
        assistance_content="Name the invariant first.",
    )

    result = _parse(gate, payload, stage="diagnostic")

    assert result.next_check is not None
    assert result.next_check.prompt == gate.prompt
    assert result.next_check.assistance.content == "Name the invariant first."


def test_assessed_response_replaces_provider_help_with_server_owned_feedback() -> None:
    gate = practice_gate()
    payload = _payload(
        gate,
        evidence_ids=[],
        next_prompt=gate.prompt,
        assistance_level="prompt",
        assistance_content="Name the invariant first.",
    )
    payload["message"] = (
        "Invented trick: divide both sides first. "
        "Name the invariant first. Diagnose the mechanism in the canonical case."
    )
    payload["assessment"]["reason"] = "Invented assessor prose."

    result = _parse(gate, payload, stage="diagnostic")

    assert result.message == (
        "More evidence is needed for the approved criterion: Names the causal boundary.\n\n"
        "Approved support:\nName the invariant first.\n\n"
        "Next check:\nDiagnose the mechanism in the canonical case."
    )
    assert result.quality_gate is not None
    assert result.quality_gate.reason == (
        "More evidence is needed for the approved criterion: Names the causal boundary."
    )
    assert "Invented" not in result.model_dump_json()


def test_server_composes_unassisted_next_check_when_provider_omits_it_from_message() -> None:
    gate = practice_gate()
    payload = _payload(
        gate,
        evidence_ids=["boundary"],
        next_prompt=gate.independent_exit_task,
        assistance_level="none",
        assistance_content=None,
    )
    payload["message"] = "Good diagnostic answer. Now try the parallel case."

    result = _parse(gate, payload, stage="diagnostic")

    assert result.message == (
        "Assessment passed against the approved required evidence.\n\n"
        f"Next check:\n{gate.independent_exit_task}"
    )


def test_exact_two_thousand_character_exit_task_is_not_truncated() -> None:
    task = "x" * 2_000
    gate = practice_gate(independent_exit_task=task)
    payload = _payload(
        gate,
        evidence_ids=["boundary"],
        next_prompt=task,
        assistance_level="none",
        assistance_content=None,
    )

    result = _parse(gate, payload, stage="diagnostic")

    assert result.next_check is not None
    assert result.next_check.prompt == task


def _parse(gate: LearningMapGate, payload: dict, *, stage: str):
    return agent_result_from_content(
        json.dumps(payload),
        AgentTurnInput(
            user_id="student-1",
            course_id="course-1",
            lecture_id="lecture-1",
            attendance=AttendanceStatus.PRESENT,
            message="Learner attempt.",
            active_gate=gate,
            coaching_context=AgentCoachingContext(
                active_gate_id=gate.id,
                active_gate_revision=gate.revision,
                pending_check_gate_id=gate.id,
                pending_check_gate_revision=gate.revision,
                pending_check_stage=stage,
                pending_check_issued_at="2026-08-26T09:00:00+00:00",
                pending_check_prompt=gate.prompt,
                exposed_hint_levels=[],
            ),
            canvas_context=_canvas(),
        ),
        "contract-model",
    )


def _payload(
    gate: LearningMapGate,
    *,
    evidence_ids: list[str],
    next_prompt: str | None,
    assistance_level: str,
    assistance_content: str | None,
) -> dict:
    support = f"{assistance_content} " if assistance_content else ""
    return {
        "message": f"{support}{next_prompt}",
        "session_goal": "Apply the mechanism independently.",
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
                "highlight_text": "causal boundary",
                "artifact_id": None,
                "section": None,
                "placement": None,
            },
        ],
        "assessment": {
            "gate_id": gate.id,
            "gate_revision": gate.revision,
            "reason": "Evidence checked against the approved criterion.",
            "evidence_ids": evidence_ids,
        },
    }


def _canvas() -> CanvasDocument:
    return CanvasDocument(
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
                        text="The causal boundary remains unchanged.",
                    )
                ],
            )
        ],
    )
