import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from lecturepilot.course_canvas_publication import CanvasPublicationMetadata
from lecturepilot.course_canvas_context import InvalidPublishedCanvasContextError
from lecturepilot.course_canvas_publication import publication_path
from lecturepilot.course_canvas_store import InvalidCanvasDraftError
from lecturepilot.course_learning_design_store import CourseLearningDesignStore
from lecturepilot.course_practice_design_binding import PracticeDesignBinding, binding_path
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
            planning_context=design.planning_context,
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


@pytest.mark.parametrize("corruption", ["missing", "malformed", "stale", "mismatch"])
def test_published_snapshot_rejects_invalid_practice_binding(
    tmp_path: Path, corruption: str
) -> None:
    workspace, design = _published_workspace(tmp_path)
    published_dir = workspace.course_canvas_store.path(design.course_id, design.lecture_id)
    path = binding_path(published_dir)
    if corruption == "missing":
        path.unlink()
    elif corruption == "malformed":
        path.write_text("{}", encoding="utf-8")
    else:
        binding = json.loads(path.read_text(encoding="utf-8"))
        binding["source_revision" if corruption == "stale" else "practice_design_revision"] = (
            "b" * 64
        )
        path.write_text(json.dumps(binding), encoding="utf-8")

    with pytest.raises(InvalidPublishedCanvasContextError, match="practice-design binding"):
        workspace.course_canvas_store.read_current_published_snapshot(
            course_id=design.course_id, lecture_id=design.lecture_id
        )


def test_legacy_published_snapshot_reads_and_republish_restores_binding(tmp_path: Path) -> None:
    workspace, design = _published_workspace(tmp_path)
    published_dir = workspace.course_canvas_store.path(design.course_id, design.lecture_id)
    metadata_path = publication_path(published_dir)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata.pop("practice_design_revision")
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    binding_path(published_dir).unlink()

    legacy = workspace.course_canvas_store.read_current_published_snapshot(
        course_id=design.course_id, lecture_id=design.lecture_id
    )
    assert legacy is not None
    assert legacy.publication.practice_design_revision is None

    republished = workspace.publish_course_canvas_draft(
        course_id=design.course_id, lecture_id=design.lecture_id, published_by="professor"
    )
    assert republished.version == 2
    assert republished.practice_design_revision == design.revision


def _published_workspace(tmp_path: Path) -> tuple[CanvasWorkspace, object]:
    workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces", material_root=tmp_path / "materials"
    )
    design = _approved_design(workspace)
    workspace.write_course_canvas_draft(
        _document(design),
        expected_source_revision=design.source_revision,
        practice_design=design,
    )
    review = CourseLearningDesignStore(workspace.layout).read(
        course_id=design.course_id, lecture_id=design.lecture_id
    )
    CourseLearningDesignStore(workspace.layout).approve(
        course_id=design.course_id,
        lecture_id=design.lecture_id,
        draft_digest=review.draft_digest,
        source_revision=review.source_revision,
        practice_design_revision=review.practice_design_revision,
        learning_map_revision=review.learning_map.revision,
        report_revision=review.report.report_revision,
        approved_by="professor",
    )
    workspace.publish_course_canvas_draft(
        course_id=design.course_id, lecture_id=design.lecture_id, published_by="professor"
    )
    return workspace, design
