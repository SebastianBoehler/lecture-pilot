import pytest

from lecturepilot.canvas_checkpoint_sequence import checkpoint_block


def test_sequence_keeps_question_and_choices_separate() -> None:
    block = checkpoint_block("check", "[sequence] Decide and explain", "Which fits?\n\n- A\n- B")
    assert block.type == "checkpoint"
    assert block.caption == "Decide and explain"
    assert block.text == "Which fits?"
    assert block.items == ["A", "B"]


@pytest.mark.parametrize(
    "text", ["Question\n- A", "Question\n- A\n- A", "- A\n- B", "Question\n- A\ntext\n- B"]
)
def test_sequence_rejects_ambiguous_or_incomplete_choices(text: str) -> None:
    with pytest.raises(ValueError):
        checkpoint_block("check", "[sequence] Decide", text)


def test_ordinary_checkpoint_keeps_original_approved_text() -> None:
    text = "Explain the result.\n- Criterion A\n- Criterion B"
    block = checkpoint_block("check", "Explain", text)
    assert block.text == text
    assert block.items == []
