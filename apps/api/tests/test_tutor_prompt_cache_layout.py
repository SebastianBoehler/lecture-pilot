from lecturepilot.agent_context_models import AgentConversationMessage
from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.model_client import _messages
from lecturepilot.models import (
    AgentCoachingContext,
    AgentTurnInput,
    AttendanceStatus,
    CanvasState,
    UserMemoryContext,
)
from lecturepilot.learning_map import LearningMapGate


def test_tutor_prompt_prefix_is_byte_stable_across_turns_and_focus_changes():
    first = _messages(_turn(focused="later", message="Explain the first idea.", late_block=True))
    second = _messages(
        _turn(
            focused="opening", message="A completely different question.", late_block=True
        ).model_copy(
            update={
                "attendance": AttendanceStatus.ABSENT,
                "user_memory": UserMemoryContext(global_notes="Prefers short examples."),
                "recent_messages": [
                    AgentConversationMessage(role="user", content="Earlier question."),
                    AgentConversationMessage(role="assistant", content="Earlier answer."),
                ],
                "coaching_context": AgentCoachingContext(
                    pending_check_prompt="A different issued question.",
                    pending_check_stage="diagnostic",
                    session_goal="A goal that changes every turn.",
                ),
            }
        )
    )

    assert _prefix(first) == _prefix(second)
    lecture = first[1]["content"]
    assert lecture.index("section_id=opening;") < lecture.index("section_id=later;")
    assert "span_id=later-extra" not in lecture
    assert "span_id=later-extra" in first[-1]["content"]
    assert "Explain the first idea." not in lecture
    assert "Explain the first idea." in first[-1]["content"]
    assert "Prefers short examples." not in _prefix(second).decode()
    assert second[2]["content"] == "Earlier question."
    assert second[3]["role"] == "assistant"
    assert "A completely different question." in second[-1]["content"]
    assert "A different issued question." not in second[1]["content"]
    assert "A different issued question." in second[-1]["content"]


def test_independent_chat_prompt_omits_the_pending_task_and_rubric():
    for stage in ("independent_exit", "delayed_transfer"):
        prompt = "\n".join(message["content"] for message in _messages(_secret_turn(stage)))
        assert "SECRET-PENDING-PROMPT" not in prompt
        assert "SECRET-GATE-PROMPT" not in prompt
        assert "SECRET-CRITERION" not in prompt
        assert "SECRET-HINT" not in prompt
        assert "withheld" in prompt


def _prefix(messages: list[dict[str, str]]) -> bytes:
    return messages[0]["content"].encode() + b"\0" + messages[1]["content"].encode()


def _turn(*, focused: str, message: str, late_block: bool) -> AgentTurnInput:
    later_blocks = [
        CanvasBlock(id=f"later-{index}", type="paragraph", text=f"Later block {index}.")
        for index in range(5)
    ]
    if late_block:
        later_blocks.append(
            CanvasBlock(
                id="later-extra", type="paragraph", text="Focused passage past the outline."
            )
        )
    return AgentTurnInput(
        user_id="student-1",
        course_id="course-1",
        lecture_id="lecture-1",
        attendance=AttendanceStatus.PRESENT,
        message=message,
        canvas_state=CanvasState(focused_section_id=focused),
        active_gate=LearningMapGate.create(
            id="opening-check",
            concept_id="opening",
            title="Opening",
            prompt="Explain the published opening claim.",
            evidence_criteria=[{"id": "claim", "description": "Name the published claim."}],
            transfer_prompt="Apply the claim in a new setting.",
            review_after_days=3,
            section_id="opening",
            source_ref=None,
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
                    id="opening",
                    title="Opening",
                    blocks=[CanvasBlock(id="opening-1", type="paragraph", text="Opening claim.")],
                ),
                CanvasSection(id="later", title="Later", blocks=later_blocks),
            ],
        ),
    )


def _secret_turn(stage: str) -> AgentTurnInput:
    gate = LearningMapGate.create(
        id="secret-check",
        concept_id="secret",
        title="Check",
        prompt="SECRET-GATE-PROMPT",
        evidence_criteria=[{"id": "secret", "description": "SECRET-CRITERION"}],
        transfer_prompt="SECRET-PENDING-PROMPT",
        review_after_days=3,
        section_id="opening",
        source_ref=None,
    )
    return AgentTurnInput(
        user_id="student-1",
        course_id="course-1",
        lecture_id="lecture-1",
        attendance=AttendanceStatus.PRESENT,
        message="Help me with the hidden check.",
        canvas_state=CanvasState(focused_section_id="opening"),
        active_gate=gate,
        coaching_context=AgentCoachingContext(
            pending_check_stage=stage,
            pending_check_prompt="SECRET-PENDING-PROMPT",
            pending_check_assistance_content="SECRET-HINT",
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
                    id="opening",
                    title="Opening",
                    blocks=[
                        CanvasBlock(id="opening-1", type="paragraph", text="Visible teaching.")
                    ],
                )
            ],
        ),
    )
