from datetime import UTC, datetime
from pathlib import Path

import pytest

from lecturepilot.course_canvas_publication import CanvasPublicationMetadata
from lecturepilot.course_canvas_store import InvalidCanvasDraftError
from lecturepilot.course_practice_design_binding import PracticeDesignBinding
from lecturepilot.course_practice_design_models import PracticeDesignUpdate
from lecturepilot.course_practice_design_store import PracticeDesignStore
from test_practice_design_canvas_binding import _approved_design, _document
from lecturepilot.canvas_workspace import CanvasWorkspace


def test_draft_rejects_post_generation_only_design_approval(tmp_path: Path) -> None:
    workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces", material_root=tmp_path / "materials"
    )
    design = _approved_design(workspace)
    store = PracticeDesignStore(workspace.layout)
    changed = store.update(
        course_id=design.course_id,
        lecture_id=design.lecture_id,
        current_source_revision=design.source_revision,
        update=PracticeDesignUpdate(
            source_revision=design.source_revision,
            practice_design_revision=design.revision,
            lecture_title=design.lecture_title,
            objective="Derive a revised conclusion independently.",
            targets=design.targets,
        ),
        allowed_source_paths=("lecture.md",),
    )

    with pytest.raises(InvalidCanvasDraftError, match="approved practice design"):
        workspace.write_course_canvas_draft(
            _document(changed),
            expected_source_revision=changed.source_revision,
            practice_design=changed,
        )


def test_publication_metadata_accepts_legacy_practice_revision_none() -> None:
    metadata = CanvasPublicationMetadata(
        schema_version=1,
        course_id="course",
        lecture_id="lecture",
        version=1,
        source_revision="a" * 64,
        draft_digest="b" * 64,
        learning_map_revision="c" * 64,
        published_at=datetime.now(UTC),
        published_by="professor",
    )

    assert metadata.practice_design_revision is None


def test_publication_metadata_rejects_practice_revision_mismatch() -> None:
    binding = PracticeDesignBinding(
        source_revision="a" * 64,
        practice_design_revision="b" * 64,
    )
    metadata = CanvasPublicationMetadata(
        schema_version=1,
        course_id="course",
        lecture_id="lecture",
        version=1,
        source_revision=binding.source_revision,
        draft_digest="c" * 64,
        learning_map_revision="d" * 64,
        practice_design_revision="e" * 64,
        published_at=datetime.now(UTC),
        published_by="professor",
    )

    assert metadata.practice_design_revision != binding.practice_design_revision
