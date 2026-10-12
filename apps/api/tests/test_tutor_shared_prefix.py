"""Two learners of one lecture must send a byte-identical cacheable request prefix."""

import json
from types import SimpleNamespace

from pydantic_ai.messages import CachePoint, ModelResponse, TextPart
from pydantic_ai.models.function import FunctionModel

from lecturepilot.tutor.agent_context_models import AgentConversationMessage, UserMemoryContext
from lecturepilot.canvas.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.learning_design.learning_map import LearningMapGate
from lecturepilot.llm.model_client import NativeModelClient
from lecturepilot.core.models import (
    AgentCoachingContext,
    AgentTurnInput,
    AttendanceStatus,
    CanvasState,
    ProviderSettings,
)

SETTINGS = ProviderSettings(
    provider="openai", model="openai/gpt-6", api_key_env="KEY", capabilities=set()
)
PUBLISHED = [
    CanvasSection(
        id="opening",
        title="Opening",
        blocks=[CanvasBlock(id="opening-1", type="paragraph", text="Opening claim.")],
    ),
    CanvasSection(
        id="later",
        title="Later",
        blocks=[CanvasBlock(id=f"later-{i}", type="paragraph", text=f"L{i}.") for i in range(7)],
    ),
]
LEARNER_NOTE = CanvasSection(
    id="b-private-note",
    title="B private note",
    blocks=[CanvasBlock(id="b-note-text", type="paragraph", text="B-ONLY-NOTE-TEXT")],
)


def _gate(gate_id: str, section_id: str) -> LearningMapGate:
    return LearningMapGate.create(
        id=gate_id,
        concept_id=section_id,
        title=f"Check {gate_id}",
        prompt=f"Explain {gate_id}.",
        evidence_criteria=[{"id": f"{gate_id}-claim", "description": "Name the claim."}],
        transfer_prompt="Apply it.",
        review_after_days=3,
        section_id=section_id,
        source_ref=None,
    )


def _canvas(sections) -> CanvasDocument:
    return CanvasDocument(
        id="course-1-lecture-1",
        course_id="course-1",
        lecture_id="lecture-1",
        title="Lecture",
        source_kind="generated",
        source_ref="lecture.md",
        workspace_path="course/index.md",
        sections=sections,
    )


def _learner_a() -> AgentTurnInput:
    return AgentTurnInput(
        user_id="student-a",
        course_id="course-1",
        lecture_id="lecture-1",
        attendance=AttendanceStatus.PRESENT,
        message="Why is the opening claim true?",
        canvas_state=CanvasState(focused_section_id="opening"),
        active_gate=_gate("opening-check", "opening"),
        canvas_context=_canvas(PUBLISHED),
    )


def _learner_b() -> AgentTurnInput:
    return AgentTurnInput(
        user_id="student-b",
        course_id="course-1",
        lecture_id="lecture-1",
        attendance=AttendanceStatus.ABSENT,
        message="Please add a note about B-ONLY-QUESTION.",
        canvas_state=CanvasState(focused_section_id="later"),
        active_gate=_gate("later-check", "later"),
        canvas_context=_canvas([PUBLISHED[0], LEARNER_NOTE, PUBLISHED[1]]),
        learner_section_ids=[LEARNER_NOTE.id],
        user_memory=UserMemoryContext(global_notes="B-ONLY-MEMORY"),
        recent_messages=[
            AgentConversationMessage(role="user", content="B-ONLY-HISTORY"),
            AgentConversationMessage(role="assistant", content="Earlier answer."),
        ],
        coaching_context=AgentCoachingContext(session_goal="B-ONLY-GOAL"),
    )


async def _first_request(turn: AgentTurnInput):
    captured = []

    def respond(messages, info):
        captured.append((messages, info))
        payload = {
            "message": "Look at the opening claim.",
            "session_goal": None,
            "canvas_commands": [
                {"type": command, "section_id": "opening", "span_id": span, "highlight_text": None}
                | {"artifact_id": None, "section": None, "placement": None}
                for command, span in (("focus_section", None), ("highlight_span", "opening-1"))
            ],
            "assessment": None,
        }
        return ModelResponse(parts=[TextPart(json.dumps(payload))])

    executor = SimpleNamespace(
        execute=lambda name, args: {"ok": True}, pending_canvas_edit_instruction=lambda: None
    )
    await NativeModelClient(model=FunctionModel(respond)).complete_turn(
        settings=SETTINGS, turn=turn, tool_executor=executor, tool_profile="tutor"
    )
    return captured[0]


def _shared_prefix(messages, info) -> bytes:
    lecture_part = messages[0].parts[0]
    assert isinstance(lecture_part.content[-1], CachePoint)
    return json.dumps(
        {
            "instructions": info.instructions,
            "tools": [
                [tool.name, tool.description, tool.parameters_json_schema]
                for tool in info.function_tools
            ],
            "output_schema": info.model_request_parameters.output_object.json_schema,
            "lecture_context": lecture_part.content[0],
            "prompt_cache_key": info.model_settings["openai_prompt_cache_key"],
        },
        sort_keys=True,
    ).encode()


async def test_shared_prefix_is_byte_identical_across_learners_of_one_lecture():
    a_messages, a_info = await _first_request(_learner_a())
    b_messages, b_info = await _first_request(_learner_b())

    a_prefix, b_prefix = _shared_prefix(a_messages, a_info), _shared_prefix(b_messages, b_info)
    assert a_prefix == b_prefix
    for private in ("student-b", "b-private-note", "B-ONLY", "later-check", "opening-check"):
        assert private.encode() not in a_prefix
    learner_turn = b_messages[-1].parts[-1].content
    for private in ("b-private-note", "B-ONLY-NOTE-TEXT", "B-ONLY-MEMORY", "B-ONLY-GOAL"):
        assert private in learner_turn
    assert "later-check" in learner_turn and "B-ONLY-QUESTION" in learner_turn
    assert "B-ONLY-HISTORY" in b_messages[0].parts[1].content  # after the cache boundary
