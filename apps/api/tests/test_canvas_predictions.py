import pytest

from lecturepilot.canvas_predictions import PredictionStore
from lecturepilot.canvas_markdown_blocks import block_to_markdown, read_blocks
from lecturepilot.canvas_models import CanvasBlock
from lecturepilot.storage_layout import StorageLayout
from test_canvas_annotations import document


def prediction_document():
    doc = document()
    doc.sections[0].blocks = [
        CanvasBlock(
            id="predict",
            type="prediction",
            caption="Before you begin",
            text="Perfect training accuracy: what do you expect on new examples, and why?",
        )
    ]
    return doc


def test_prediction_markdown_roundtrip():
    block = prediction_document().sections[0].blocks[0]
    assert read_blocks(
        block_to_markdown(block), section_id="section", course_id="course", lecture_id="lecture"
    ) == [block]


def test_private_first_prediction_revision_and_skip(tmp_path):
    layout = StorageLayout(tmp_path)
    store = PredictionStore(layout, "alice", "course", "lecture")
    doc = prediction_document()
    saved = store.save(doc, 1, "predict", "It will also be perfect.")
    assert store.list(doc, 1) == [saved]
    assert PredictionStore(layout, "bob", "course", "lecture").list(doc, 1) == []
    assert store.list(doc, 2) == []
    assert store.save(doc, 1, "predict", saved.answer) == saved
    with pytest.raises(ValueError, match="already saved"):
        store.save(doc, 1, "predict", "Changed my mind")
    skipped = store.save(doc, 2, "predict", None)
    assert skipped.answer is None
    assert store.list(doc, 2) == [skipped]
    doc.sections[0].blocks[0].text = "Changed question"
    assert store.list(doc, 2) == []
    for block, answer in [("missing", "Guess"), ("predict", "  ")]:
        with pytest.raises(ValueError):
            store.save(doc, 3, block, answer)
    assert not list(layout.root.rglob("gates.json"))


def test_predictions_reject_symlinked_storage(tmp_path):
    layout = StorageLayout(tmp_path)
    root = layout.user_lecture_root("alice", "course", "lecture")
    root.parent.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    root.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError):
        PredictionStore(layout, "alice", "course", "lecture")


def test_predictions_do_not_replace_assessments_or_multiply():
    from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
    from lecturepilot.course_canvas_validation import validate_planned_document

    doc = prediction_document()
    with pytest.raises(CanvasGenerationRepairableError, match="checkpoint"):
        validate_planned_document(doc, doc)
    doc.sections[0].blocks.append(doc.sections[0].blocks[0].model_copy(update={"id": "second"}))
    with pytest.raises(CanvasGenerationRepairableError, match="at most one"):
        validate_planned_document(doc, doc)
