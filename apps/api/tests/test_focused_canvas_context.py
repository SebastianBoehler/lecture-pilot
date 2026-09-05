from lecturepilot.canvas_models import CanvasBlock
from lecturepilot.model_commands import canvas_context
from test_strict_model_payload import _turn


def test_focused_section_includes_passages_after_the_fifth_block():
    turn = _turn()
    section = turn.canvas_context.sections[0]
    section.blocks = [
        CanvasBlock(id=f"intro-{i}", type="paragraph", text="Introductory definition.")
        for i in range(6)
    ] + [
        CanvasBlock(
            id="generalization", type="paragraph", text="Unseen data measures generalization."
        )
    ]
    turn.canvas_state.focused_section_id = section.id
    context = canvas_context(turn)
    assert "span_id=generalization" in context
    assert "Unseen data measures generalization." in context
    assert len(context) <= 9000


def test_focused_section_precedes_unfocused_sections_in_the_context_budget():
    turn = _turn()
    section = turn.canvas_context.sections[0]
    focused = section.model_copy(update={"id": "later", "title": "Later section"})
    turn.canvas_context.sections = [section, focused]
    turn.canvas_state.focused_section_id = "later"
    context = canvas_context(turn)
    assert context.index("section_id=later;") < context.index("section_id=mechanism;")
