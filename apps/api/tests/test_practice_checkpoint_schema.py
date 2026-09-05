from lecturepilot.course_canvas_response_schema import canvas_block_schema
from lecturepilot.course_canvas_section_prompt import section_messages
from practice_design_test_helpers import practice_design_for_canvas
from test_course_canvas_section_concurrency import _source_document


def test_strict_checkpoint_schema_can_return_the_required_canonical_id():
    checkpoint = next(
        item
        for item in canvas_block_schema()["anyOf"]
        if item["properties"]["type"].get("const") == "checkpoint"
    )
    assert checkpoint["properties"]["id"] == {"type": ["string", "null"]}
    assert "id" in checkpoint["required"]
    assert checkpoint["additionalProperties"] is False


def test_section_prompt_exempts_approved_practice_ids_from_server_generated_ids():
    source = _source_document(1)
    design = practice_design_for_canvas(source)
    messages = section_messages(
        source, source.sections[0], practice_design=design, applicable_targets=design.targets
    )
    assert (
        "For approved practice checkpoints, return their exact canonical id"
        in messages[0]["content"]
    )
