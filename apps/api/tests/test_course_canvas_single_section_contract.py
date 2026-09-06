import pytest

from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_canvas_section_payload import section_payload


def test_single_section_reader_never_discards_extra_sections():
    with pytest.raises(CanvasGenerationRepairableError, match="exactly one section"):
        section_payload(
            {
                "sections": [
                    {"title": "Classification", "blocks": [{"id": "practice-t2"}]},
                    {"title": "Generalization", "blocks": [{"id": "practice-t3"}]},
                ]
            }
        )


def test_single_section_provider_schema_enforces_cardinality_without_changing_full_schema():
    from lecturepilot.agent_response_schema import (
        course_canvas_response_format,
        course_canvas_section_response_format,
    )

    sections = course_canvas_section_response_format()["json_schema"]["schema"]["properties"][
        "sections"
    ]
    assert sections["minItems"] == sections["maxItems"] == 1
    checkpoint = next(
        block
        for block in sections["items"]["properties"]["blocks"]["items"]["anyOf"]
        if block["properties"]["type"].get("const") == "checkpoint"
    )
    assert checkpoint["properties"]["id"] == {"type": "null"}
    full = course_canvas_response_format()["json_schema"]["schema"]["properties"]["sections"]
    assert "maxItems" not in full
