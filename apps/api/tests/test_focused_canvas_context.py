from lecturepilot.canvas_models import CanvasBlock
from lecturepilot.model_commands import canvas_outline_stable, focused_section_blocks
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
    outline = canvas_outline_stable(turn)
    focused = focused_section_blocks(turn)
    assert "span_id=generalization" not in outline
    assert "span_id=generalization" in focused
    assert "Unseen data measures generalization." in focused
    assert len(outline) <= 9000
    assert len(focused) <= 9000


def test_canvas_outline_keeps_document_order_when_focus_changes():
    turn = _turn()
    section = turn.canvas_context.sections[0]
    later = section.model_copy(update={"id": "later", "title": "Later section"})
    turn.canvas_context.sections = [section, later]
    turn.canvas_state.focused_section_id = "later"
    context = canvas_outline_stable(turn)
    assert context.index("section_id=mechanism;") < context.index("section_id=later;")
