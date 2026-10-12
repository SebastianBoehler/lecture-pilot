import pytest

from lecturepilot.learning_design.course_learning_intent_store import LearningIntentStore
from lecturepilot.learning_design.course_practice_design_models import PracticeDesignProposal
from lecturepilot.learning_design.course_practice_design_store import PracticeDesignStore
from lecturepilot.core.storage_layout import StorageLayout
from approved_practice_design_helpers import approved_practice_design, store_design
from practice_design_test_helpers import passing_review, proposal, source_document


def stored(tmp_path):
    """AI-generated teaching for goals that are not approved yet."""
    layout = StorageLayout(tmp_path)
    design = store_design(
        layout,
        approved_practice_design(
            course_id="course-01",
            lecture_id="lecture-01",
            source_revision="a" * 64,
            targets=proposal().targets,
            approved=False,
        ),
    )
    return PracticeDesignStore(layout), design


def approve(store, design, **kwargs):
    return LearningIntentStore(store.layout).approve(
        course_id=design.course_id,
        lecture_id=design.lecture_id,
        source_revision=design.source_revision,
        design_revision=design.revision,
        approved_by="professor",
        **kwargs,
    )


def repair(store, design, **changes):
    initial = PracticeDesignProposal(
        **{
            key: getattr(design, key)
            for key in ("lecture_title", "objective", "planning_context", "targets")
        }
    )
    return LearningIntentStore(store.layout).save_implementation(
        expected=design,
        proposal=initial.model_copy(update=changes),
        review=passing_review(),
        source=source_document(),
        allowed_source_paths=("lecture-01.md",),
    )


def test_repair_preserves_approved_intent_but_changes_implementation(tmp_path):
    store, original = stored(tmp_path)
    approved = approve(store, original)
    changed = repair(
        store,
        approved,
        targets=(
            approved.targets[0].model_copy(
                update={
                    "baseline_task": "Use the supplied evidence to derive and justify a conclusion.",
                }
            ),
        ),
    )
    assert changed.learning_intent == approved.learning_intent
    assert changed.revision != approved.revision
    assert (
        store.require_approved(
            course_id=changed.course_id,
            lecture_id=changed.lecture_id,
            source_revision=changed.source_revision,
        )
        == changed
    )


@pytest.mark.parametrize("change", ["goal", "constraint", "fixed_task"])
def test_repair_cannot_change_protected_intent_even_with_passing_review(tmp_path, change):
    store, design = stored(tmp_path)
    approved = approve(store, design, fixed_target_ids=(design.targets[0].id,))
    changes = {"objective": "Drop the difficult conclusion."}
    if change == "constraint":
        changes = {
            "planning_context": approved.planning_context.model_copy(
                update={
                    "time_budget_minutes": 1,
                }
            )
        }
    if change == "fixed_task":
        changes = {
            "targets": (
                approved.targets[0].model_copy(
                    update={
                        "baseline_task": "State anything without justification.",
                    }
                ),
            )
        }
    with pytest.raises(ValueError, match="protected"):
        repair(store, approved, **changes)
    assert store.read(course_id=design.course_id, lecture_id=design.lecture_id) == approved


def test_goal_approval_archives_the_previous_design(tmp_path):
    store, design = stored(tmp_path)
    approved = approve(store, design)
    assert approved.learning_intent.approval is not None
    assert approved.revision == design.revision
    assert any('"approval": null' in path.read_text() for path in tmp_path.rglob("history/*.json"))


def test_racing_intent_approval_invalidates_pending_implementation(tmp_path):
    store, design = stored(tmp_path)
    first = approve(store, design)
    latest = approve(store, first, fixed_target_ids=(design.targets[0].id,))
    with pytest.raises(ValueError, match="changed"):
        repair(store, first)
    assert store.read(course_id=design.course_id, lecture_id=design.lecture_id) == latest


def test_implementation_report_records_exact_changes_without_changing_goals(tmp_path):
    import json

    store, original = stored(tmp_path)
    approved = approve(store, original)
    changed = repair(
        store,
        approved,
        targets=(
            approved.targets[0].model_copy(
                update={
                    "baseline_task": "Derive a conclusion using the supplied evidence and justify it."
                }
            ),
        ),
    )
    path = store.layout.lecture_practice_design_path(changed.course_id, changed.lecture_id)
    report = json.loads(
        (
            path.parent / path.stem / "implementation-changes" / f"{changed.revision}.json"
        ).read_text()
    )
    assert report["from_revision"] == approved.revision
    assert report["to_revision"] == changed.revision
    assert report["learning_intent_revision"] == approved.learning_intent.revision
    assert report["changes"] == [
        {
            "target_id": changed.targets[0].id,
            "target_title": changed.targets[0].title,
            "field": "baseline_task",
            "before": approved.targets[0].baseline_task,
            "after": changed.targets[0].baseline_task,
        }
    ]


def test_professor_removal_rebinds_remaining_teaching_and_fixed_targets(tmp_path):
    from lecturepilot.learning_design.course_learning_intent_proposal import LearningIntentProposal

    store, design = stored(tmp_path)
    first = design.targets[0]
    design = store_design(
        store.layout,
        approved_practice_design(
            course_id=design.course_id,
            lecture_id=design.lecture_id,
            source_revision=design.source_revision,
            targets=(first, first.model_copy(update={"id": "second-goal"})),
            approved=False,
            reviewed=False,
        ),
    )
    approved = approve(store, design, fixed_target_ids=tuple(t.id for t in design.targets))
    intent = approved.learning_intent
    edited = LearningIntentStore(store.layout).save_goals(
        expected=approved,
        course_id=design.course_id,
        lecture_id=design.lecture_id,
        source_revision=design.source_revision,
        proposal=LearningIntentProposal(
            lecture_title=design.lecture_title,
            objective=intent.objective,
            planning_context=intent.planning_context,
            goals=intent.goals[:1],
        ),
        source=source_document(),
        allowed_source_paths=("lecture-01.md",),
    )
    assert [t.id for t in edited.targets] == [design.targets[0].id]
    assert [t.id for t in edited.learning_intent.fixed_targets] == [design.targets[0].id]
    assert edited.learning_intent.approval is None
    assert edited.quality_review is None
    assert edited.revision != approved.revision
