import pytest

from lecturepilot.agent_context_models import AgentConversationMessage
from lecturepilot.models import AgentTurnInput, AttendanceStatus
from lecturepilot.tutor_turn_budget import (
    CHAT_OUTPUT_TOKEN_LIMIT,
    WRITING_OUTPUT_TOKEN_LIMIT,
    tutor_quota_reservation,
    tutor_turn_budget,
)


def _turn(message: str, *, previous: str | None = None, checkpoint: bool = False):
    history = (
        [
            AgentConversationMessage(role="user", content="Earlier question."),
            AgentConversationMessage(role="assistant", content=previous),
        ]
        if previous
        else []
    )
    return AgentTurnInput(
        user_id="student-1",
        course_id="course-1",
        lecture_id="lecture-1",
        attendance=AttendanceStatus.PRESENT,
        message=message,
        checkpoint_gate_id="gate-1" if checkpoint else None,
        recent_messages=history,
    )


@pytest.mark.parametrize(
    "message",
    [
        "Why does the gradient vanish here?",
        "I think the answer is 42 because the loss is convex.",
        "Can you explain this table?",
        "Was bedeutet diese Formel?",
    ],
)
def test_ordinary_chat_gets_a_small_output_cap(message):
    budget = tutor_turn_budget(_turn(message), tools=True)
    assert budget.kind == "chat"
    assert budget.max_tokens == 2_048
    assert budget.output_tokens_limit == CHAT_OUTPUT_TOKEN_LIMIT


@pytest.mark.parametrize(
    "message",
    [
        "Please add a note with a worked example to the canvas.",
        "Create a diagram comparing both algorithms.",
        "Generate an image of a neuron.",
        "Füge bitte eine Zusammenfassung hinzu.",
        "Kannst du eine Tabelle erstellen?",
    ],
)
def test_explicit_canvas_writing_gets_the_large_cap(message):
    budget = tutor_turn_budget(_turn(message), tools=True)
    assert budget.kind == "canvas_write"
    assert budget.max_tokens == 8_192
    assert budget.output_tokens_limit == WRITING_OUTPUT_TOKEN_LIMIT


def test_accepting_a_previous_write_offer_keeps_the_writing_cap():
    turn = _turn("Yes please.", previous="Shall I add a summary section for this proof?")
    assert tutor_turn_budget(turn, tools=True).kind == "canvas_write"


def test_turns_without_tools_keep_the_assessment_cap():
    budget = tutor_turn_budget(_turn("Add a note.", checkpoint=True), tools=False)
    assert (budget.kind, budget.max_tokens) == ("assessment", 1_500)


def test_quota_reservation_follows_the_chosen_output_cap():
    writing = tutor_quota_reservation(_turn("Add a note."), writing_turn_reservation=16_000)
    chat = tutor_quota_reservation(_turn("Why?"), writing_turn_reservation=16_000)
    checkpoint = tutor_quota_reservation(
        _turn("My answer.", checkpoint=True), writing_turn_reservation=16_000
    )
    assert writing == 16_000
    assert chat == checkpoint == 16_000 - (WRITING_OUTPUT_TOKEN_LIMIT - CHAT_OUTPUT_TOKEN_LIMIT)
    assert tutor_quota_reservation(_turn("Why?"), writing_turn_reservation=10) == 4_096
