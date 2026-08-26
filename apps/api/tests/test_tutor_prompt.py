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
        active_gate=LearningMapGate.create(
            id="causal-transfer-check",
            concept_id="causal-transfer",
            title="Causal transfer",
            prompt="Explain when the conclusion transfers.",
            evidence_criteria=[{"id": "boundary", "description": "Name a transfer boundary."}],
            transfer_prompt="Apply the conclusion to an unfamiliar setting.",
            review_after_days=3,
            section_id="causal-transfer",
            source_ref=None,
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
    assert "assistance actually contained in message" in system_prompt
    assert "next approved support selected by the server" in system_prompt
    assert "highlight_span" in system_prompt


def test_model_prompt_uses_declarative_visuals_without_raster_fallback() -> None:
    system_prompt = _messages(_turn())[0]["content"].lower()

    assert "visual_artifact" in system_prompt
    assert "flow, timeline, grid, or plot" in system_prompt
    assert "never use image generation as a fallback" in system_prompt


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


def test_model_prompt_includes_the_approved_practice_teaching_contract() -> None:
    gate = LearningMapGate.create(
        id="practice-causal-transfer",
        concept_id="causal-transfer",
        title="Causal transfer",
        prompt="Explain when the conclusion transfers.",
        target_invariant="Apply the same causal boundary reasoning.",
        evidence_criteria=[{"id": "boundary", "description": "Name a transfer boundary."}],
        transfer_prompt="Apply the conclusion to an unfamiliar setting.",
        independent_exit_task="Apply the boundary independently to a parallel setting.",
        independent_exit_surface_change="Change the setting while preserving the boundary.",
        delayed_transfer_surface_change="Change the representation and setting.",
        misconceptions=[
            {
                "id": "surface-match",
                "description": "Transfers from superficial similarity alone.",
                "diagnostic_cue": "The response never checks the causal boundary.",
            }
        ],
        hint_ladder=[{"level": "prompt", "content": "Identify the causal boundary first."}],
        review_after_days=3,
        section_id="causal-transfer",
        source_ref="lecture.md",
        practice_target_id="causal-transfer",
    )
    prompt = _messages(_turn().model_copy(update={"active_gate": gate}))[1]["content"]

    for value in (
        gate.target_invariant,
        gate.independent_exit_task,
        gate.independent_exit_surface_change,
        gate.delayed_transfer_surface_change,
        gate.misconceptions[0].id,
        gate.misconceptions[0].description,
        gate.misconceptions[0].diagnostic_cue,
        gate.hint_ladder[0].level,
        gate.hint_ladder[0].content,
    ):
        assert value in prompt
