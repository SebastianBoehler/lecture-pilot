from lecturepilot.learning_map import LearningMapGate
from lecturepilot.model_client import _messages
from lecturepilot.models import (
    AgentCoachingContext,
    AgentTurnInput,
    AttendanceStatus,
    CanvasState,
)
from lecturepilot.scaffold_policy import scaffold_policy_for_tutor_turn


def _turn() -> AgentTurnInput:
    return AgentTurnInput(
        user_id="student01",
        course_id="martius-ml",
        lecture_id="lecture-14",
        attendance=AttendanceStatus.UNKNOWN,
        message="hello",
        canvas_state=CanvasState(focused_section_id="causal-transfer"),
        active_gate=LearningMapGate(
            id="causal-transfer-check",
            concept_id="causal-transfer",
            title="Causal transfer",
            prompt="Explain when the conclusion transfers.",
            evidence_criteria=[{"id": "boundary", "description": "Name a transfer boundary."}],
            section_id="causal-transfer",
        ),
    )


def test_model_prompt_requires_guided_quality_gate_turns() -> None:
    system_prompt = _messages(_turn())[0]["content"].lower()

    assert "do not ask open-ended" in system_prompt
    assert "do not mark a gate passed from keywords" in system_prompt
    assert "definition, mechanism, computation, and transfer" not in system_prompt
    assert "attendance selects the tutor stance" in system_prompt
    assert "next similar task without lecturepilot" in system_prompt
    assert "never ask the learner to select a learning style" in system_prompt
    assert "delayed independent transfer check" in system_prompt
    assert "support actually contained in message" in system_prompt
    assert "post-attempt corrective cue" in system_prompt
    assert "highlight_span" in system_prompt


def test_model_prompt_includes_derived_coaching_goal_and_support_policy() -> None:
    turn = _turn().model_copy(
        update={
            "coaching_context": AgentCoachingContext(
                session_goal="Explain causal transfer and apply it to a new setting.",
                goal_is_new=True,
            ),
            "scaffold_policy": scaffold_policy_for_tutor_turn(
                attendance="present",
                delayed_transfer_due=False,
                last_gate_status=None,
                needs_evidence_count=0,
                prior_assistance=False,
            ),
        }
    )

    user_prompt = _messages(turn)[1]["content"]
    assert "Explain causal transfer and apply it to a new setting." in user_prompt
    assert "goal_status: proposed" in user_prompt
    assert "profile: self_explanation" in user_prompt
    assert "Ask for the learner's own attempt" in user_prompt
