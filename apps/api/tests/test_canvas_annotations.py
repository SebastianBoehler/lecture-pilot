import pytest

from lecturepilot.canvas_annotations import AnnotationStore
from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.storage_layout import StorageLayout


def document(text="Classification predicts a discrete label."):
    return CanvasDocument(
        id="canvas",
        course_id="course",
        lecture_id="lecture",
        title="Lecture",
        source_kind="generated",
        source_ref="test",
        workspace_path="test",
        sections=[
            CanvasSection(
                id="section",
                title="Classification",
                blocks=[CanvasBlock(id="block", type="paragraph", text=text)],
            )
        ],
    )


def test_annotations_persist_privately_and_bind_to_exact_content(tmp_path):
    layout = StorageLayout(tmp_path)
    store = AnnotationStore(layout, "alice", "course", "lecture")
    note = store.save(
        document(),
        1,
        "classification",
        {"block_id": "block", "quote": "discrete label", "comment": "Think of digit categories."},
    )
    assert AnnotationStore(layout, "alice", "course", "lecture").list(document(), 1) == [note]
    assert AnnotationStore(layout, "bob", "course", "lecture").list(document(), 1) == []
    assert store.list(document(), 2) == []
    assert store.list(document("Classification uses categories."), 1) == []
    assert (
        store.save(
            document(),
            1,
            "classification",
            {
                "block_id": "block",
                "quote": "discrete label",
                "comment": "Think of digit categories.",
            },
        )
        == note
    )
    store.delete(note.id)
    assert store.list(document(), 1) == []


def test_annotation_rejects_invented_targets_and_blank_comments(tmp_path):
    store = AnnotationStore(StorageLayout(tmp_path), "alice", "course", "lecture")
    for block, quote, comment in [
        ("missing", "", "Note"),
        ("block", "invented quote", "Note"),
        ("block", "", "   "),
    ]:
        with pytest.raises(ValueError):
            store.save(
                document(), 1, "note", {"block_id": block, "quote": quote, "comment": comment}
            )


def test_annotation_rejects_symlinked_learner_storage(tmp_path):
    layout = StorageLayout(tmp_path)
    root = layout.user_lecture_root("alice", "course", "lecture")
    root.parent.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    root.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError):
        AnnotationStore(layout, "alice", "course", "lecture")
    assert not (outside / "annotations").exists()


def test_updates_keep_identity_and_reject_stale_or_foreign_annotations(tmp_path):
    layout = StorageLayout(tmp_path)
    store = AnnotationStore(layout, "alice", "course", "lecture")
    note = store.save(
        document(),
        1,
        "note",
        {"block_id": "block", "quote": "discrete label", "comment": "Old comment"},
    )
    updated = store.save(
        document(), 1, note.id, {**note.model_dump(), "comment": "**Updated** comment"}
    )
    assert updated.id == note.id and updated.created_at == note.created_at
    assert updated.quote == note.quote
    assert store.list(document(), 1) == [updated]
    for owner, version, block, comment in [
        ("bob", 1, "block", "Foreign"),
        ("alice", 2, "block", "Stale"),
        ("alice", 1, "other", "Moved"),
        ("alice", 1, "block", "  "),
    ]:
        with pytest.raises(ValueError):
            AnnotationStore(layout, owner, "course", "lecture").save(
                document(),
                version,
                note.id,
                {**note.model_dump(), "block_id": block, "comment": comment},
            )
    assert store.list(document(), 1) == [updated]
