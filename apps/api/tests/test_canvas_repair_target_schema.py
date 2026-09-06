import pytest

from lecturepilot.course_canvas_repair_response import repair_patch_response_format


def test_patch_schema_binds_target_ids_and_exact_edit_count():
    schema = repair_patch_response_format(section_id="topic", block_ids=["first", "second"])
    edits = schema["json_schema"]["schema"]["properties"]["edits"]
    assert edits["minItems"] == edits["maxItems"] == 2
    fields = edits["items"]["properties"]
    assert fields["section_id"]["enum"] == ["topic"]
    assert fields["block_id"]["enum"] == ["first", "second"]


@pytest.mark.parametrize("ids", [[], ["same", "same"]])
def test_patch_schema_rejects_invalid_target_scope(ids):
    with pytest.raises(ValueError, match="distinct"):
        repair_patch_response_format(section_id="topic", block_ids=ids)
