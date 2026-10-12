import json

from lecturepilot.learning_design.course_learning_intent import digest, has_approved_intent
from lecturepilot.learning_design.course_practice_design_store import PracticeDesignStore
from lecturepilot.core.storage_layout import StorageLayout
from lecturepilot.migrations_storage.storage_migration_practice_design_schema import migrate
from practice_design_review_test_helpers import passing_review
from practice_design_test_helpers import proposal

SOURCE = "a" * 64


def legacy_payload(*, approved=True, stale_approval=False, review=True):
    """A schema-1 design exactly as the retired full-plan store wrote it."""
    draft = proposal()
    second = draft.targets[0].model_copy(update={"id": "second-target", "title": "Second"})
    payload = {
        "schema_version": 1,
        "course_id": "course-1",
        "lecture_id": "lecture-01",
        "lecture_title": draft.lecture_title,
        "objective": draft.objective,
        "planning_context": draft.planning_context.model_dump(mode="json"),
        "source_revision": SOURCE,
        "targets": [t.model_dump(mode="json") for t in (draft.targets[0], second)],
    }
    revision = digest(payload)
    review_payload = {
        "source_revision": SOURCE,
        "practice_design_revision": revision,
        "checks": passing_review().model_dump(mode="json")["checks"],
    }
    return {
        **payload,
        "learning_intent": None,
        "revision": revision,
        "quality_review": review_payload if review else None,
        "approval": {
            "approved_by": "prof-original",
            "approved_at": "2026-05-01T10:00:00Z",
            "source_revision": SOURCE,
            "practice_design_revision": "f" * 64 if stale_approval else revision,
        }
        if approved
        else None,
    }


def write(tmp_path, payload):
    layout = StorageLayout(tmp_path)
    path = layout.lecture_practice_design_path("course-1", "lecture-01")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))
    return layout, path


def test_approved_legacy_design_becomes_fully_fixed_goal_approval(tmp_path):
    legacy = legacy_payload()
    layout, path = write(tmp_path, legacy)

    dry = migrate(tmp_path)
    assert dry["converted_approved"] == [str(path.relative_to(tmp_path))]
    assert json.loads(path.read_text()) == legacy

    assert migrate(tmp_path, apply=True)["converted_approved"]
    design = PracticeDesignStore(layout).require_approved(
        course_id="course-1", lecture_id="lecture-01", source_revision=SOURCE
    )
    intent = design.learning_intent
    assert has_approved_intent(design)
    assert intent.approval.approved_by == "prof-original"
    assert intent.approval.approved_at.isoformat().startswith("2026-05-01T10:00")
    assert [goal.id for goal in intent.goals] == ["derive-conclusion", "second-target"]
    assert [fixed.id for fixed in intent.fixed_targets] == ["derive-conclusion", "second-target"]
    assert [t.model_dump(mode="json") for t in design.targets] == legacy["targets"]
    assert design.objective == legacy["objective"]
    assert design.planning_context.model_dump(mode="json") == legacy["planning_context"]
    assert design.quality_review.practice_design_revision == design.revision
    archived = list((path.parent / path.stem / "history").glob("*.json"))
    assert [json.loads(item.read_text()) for item in archived] == [legacy]

    again = migrate(tmp_path, apply=True)
    assert again["current"] == 1 and not again["converted_approved"]


def test_unapproved_and_stale_legacy_designs_keep_goals_unapproved(tmp_path):
    for payload in (legacy_payload(approved=False), legacy_payload(stale_approval=True)):
        layout, _ = write(tmp_path, payload)
        assert migrate(tmp_path, apply=True)["converted_unapproved"]
        design = PracticeDesignStore(layout).read(course_id="course-1", lecture_id="lecture-01")
        assert design.learning_intent.approval is None
        assert design.learning_intent.fixed_targets == ()
        assert len(design.targets) == 2


def test_schema_two_designs_only_lose_the_null_approval_key(tmp_path):
    layout, path = write(tmp_path, legacy_payload(approved=False))
    migrate(tmp_path, apply=True)
    current = json.loads(path.read_text())
    path.write_text(json.dumps({**current, "approval": None}))

    report = migrate(tmp_path, apply=True)
    assert report["stripped_null_approval"] == [str(path.relative_to(tmp_path))]
    assert json.loads(path.read_text()) == current


def test_invalid_legacy_designs_are_reported_and_left_untouched(tmp_path):
    tampered = {**legacy_payload(), "objective": "Changed after approval."}
    _, path = write(tmp_path, tampered)
    report = migrate(tmp_path, apply=True)
    assert report["invalid"][0]["path"] == str(path.relative_to(tmp_path))
    assert json.loads(path.read_text()) == tampered

    unreviewed = legacy_payload(review=False)
    path.write_text(json.dumps(unreviewed))
    assert migrate(tmp_path, apply=True)["invalid"]
    assert json.loads(path.read_text()) == unreviewed
