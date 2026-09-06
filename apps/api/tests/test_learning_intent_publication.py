import json

import pytest
from pydantic import ValidationError

from lecturepilot.course_canvas_publication import CanvasPublicationMetadata

from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.course_canvas_context import InvalidPublishedCanvasContextError
from lecturepilot.course_learning_intent_store import LearningIntentStore
from lecturepilot.course_learning_design_store import CourseLearningDesignStore
from lecturepilot.course_practice_design_binding import binding_path
from test_practice_design_canvas_binding import _approved_design, _document
from test_practice_design_publication import _published_workspace


def convert(workspace, design):
    return LearningIntentStore(workspace.layout).approve(
        course_id=design.course_id,
        lecture_id=design.lecture_id,
        source_revision=design.source_revision,
        design_revision=design.revision,
        approved_by="professor",
        convert_legacy=True,
    )


def test_converting_intent_does_not_change_published_tasks_or_learner_gate_revisions(tmp_path):
    workspace, legacy = _published_workspace(tmp_path)

    def read():
        return workspace.course_canvas_store.read_current_published_snapshot(
            course_id=legacy.course_id,
            lecture_id=legacy.lecture_id,
        )

    before = read()
    converted = convert(workspace, legacy)
    after = read()
    assert converted.revision != legacy.revision
    assert after.document == before.document
    assert after.publication == before.publication
    assert after.learning_map == before.learning_map


def test_publication_binds_intent_and_rejects_a_tampered_intent_binding(tmp_path):
    workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces", material_root=tmp_path / "materials"
    )
    design = convert(workspace, _approved_design(workspace))
    workspace.write_course_canvas_draft(
        _document(design), expected_source_revision=design.source_revision, practice_design=design
    )
    store = CourseLearningDesignStore(workspace.layout)
    review = store.read(course_id=design.course_id, lecture_id=design.lecture_id)
    assert review.learning_intent_revision == design.learning_intent.revision
    store.approve(
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
    snapshot = workspace.course_canvas_store.read_current_published_snapshot(
        course_id=design.course_id, lecture_id=design.lecture_id
    )
    assert snapshot.publication.learning_intent_revision == design.learning_intent.revision
    path = binding_path(workspace.course_canvas_store.path(design.course_id, design.lecture_id))
    binding = json.loads(path.read_text())
    binding["learning_intent_revision"] = "0" * 64
    path.write_text(json.dumps(binding))
    with pytest.raises(InvalidPublishedCanvasContextError, match="practice-design binding"):
        workspace.course_canvas_store.read_current_published_snapshot(
            course_id=design.course_id, lecture_id=design.lecture_id
        )


def test_intent_publication_cannot_omit_the_teaching_implementation_revision(tmp_path):
    workspace, legacy = _published_workspace(tmp_path)
    snapshot = workspace.course_canvas_store.read_current_published_snapshot(
        course_id=legacy.course_id, lecture_id=legacy.lecture_id
    )
    payload = snapshot.publication.model_dump()
    payload.update(learning_intent_revision="a" * 64, practice_design_revision=None)
    with pytest.raises(ValidationError, match="implementation revision"):
        CanvasPublicationMetadata.model_validate(payload)
