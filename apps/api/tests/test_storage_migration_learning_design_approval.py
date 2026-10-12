import json

from lecturepilot.learning_design.course_learning_design_store import review_path
from lecturepilot.migrations_storage.storage_migration_learning_design_approval import migrate
from test_learning_design_review_routes import _client_with_draft


def legacy_approval(review: dict, **changes) -> dict:
    """An approval exactly as the retired six-hash binding stored it."""
    return {
        "approved_by": "prof01",
        "approved_at": "2026-09-01T10:00:00Z",
        "draft_digest": review["draft_digest"],
        "source_revision": review["source_revision"],
        "practice_design_revision": review["practice_design_revision"],
        "learning_intent_revision": review["learning_intent_revision"],
        "learning_map_revision": review["learning_map"]["revision"],
        "report_revision": review["report"]["report_revision"],
        "acknowledged_warning_ids": [],
        **changes,
    }


def setup(tmp_path, **changes):
    client = _client_with_draft(tmp_path)
    workspace = client.app.state.canvas_workspace
    path = review_path(workspace.layout.course_canvas_draft_dir("design-course", "lecture-01"))
    review = json.loads(path.read_text())
    path.write_text(json.dumps({**review, "approval": legacy_approval(review, **changes)}))
    return workspace, path, review


def test_current_legacy_approval_is_reduced_and_still_publishes(tmp_path):
    workspace, path, review = setup(tmp_path)
    root = workspace.layout.root
    name = str(path.relative_to(root))

    assert migrate(root)["reduced"] == [name]
    assert "report_revision" in json.loads(path.read_text())["approval"]

    assert migrate(root, apply=True)["reduced"] == [name]
    approval = json.loads(path.read_text())["approval"]
    assert approval == {
        "approved_by": "prof01",
        "approved_at": "2026-09-01T10:00:00Z",
        "draft_digest": review["draft_digest"],
        "source_revision": review["source_revision"],
        "practice_design_revision": review["practice_design_revision"],
    }
    assert migrate(root, apply=True)["current"] == 1
    published = workspace.publish_course_canvas_draft(
        course_id="design-course", lecture_id="lecture-01", published_by="prof01"
    )
    assert published.draft_digest == review["draft_digest"]


def test_stale_legacy_approval_is_cleared_instead_of_revived(tmp_path):
    workspace, path, _ = setup(tmp_path, report_revision="0" * 64)
    report = migrate(workspace.layout.root, apply=True)
    assert report["cleared_stale"] == [str(path.relative_to(workspace.layout.root))]
    assert json.loads(path.read_text())["approval"] is None
