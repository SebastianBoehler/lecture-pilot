import json
from datetime import UTC, datetime

from lecturepilot.learner.coaching_progress import CoachingProgressStore
from lecturepilot.learner.coaching_state_models import PendingCheck, review_key
from lecturepilot.learner.coaching_goal_evidence import GoalEvidence
from lecturepilot.storage_migrations import MIGRATIONS
from test_generic_checkpoint_reviews import save_legacy_review
from test_review_checkpoint_routes import setup


def migration():
    return dict(MIGRATIONS)["2026-10-generic-checkpoint-reviews"]


def test_migration_reports_invalid_maps_without_rewriting_them(tmp_path):
    path = tmp_path / "courses/tenant/course/canvas/lectures/lecture/learning-map.json"
    path.parent.mkdir(parents=True)
    path.write_text('{"broken": true}')

    report = migration()(tmp_path, apply=True)

    assert report["updated"] == []
    assert report["invalid"] == [str(path.relative_to(tmp_path))]
    assert path.read_text() == '{"broken": true}'


def test_retire_generic_reviews_without_changing_publications_or_immediate_evidence(tmp_path):
    client, gate, ids, _ = setup(tmp_path)
    root = client.app.state.canvas_workspace.workspace_root
    save_legacy_review(client, gate, ids)
    store = CoachingProgressStore(client.app.state.canvas_workspace.layout)
    progress = store.read(**ids)
    key = review_key(gate.id, gate.revision)
    progress.goal_evidence[key] = GoalEvidence(
        gate_id=gate.id, gate_revision=gate.revision, independent=True, delayed=True
    )
    progress.pending_check = PendingCheck(
        gate_id=gate.id,
        gate_revision=gate.revision,
        prompt=progress.delayed_reviews[key].transfer_prompt,
        task_id="delayed-transfer",
        assistance_level="none",
        assistance_content=None,
        kind="delayed_transfer",
        stage="delayed_transfer",
        issued_at=datetime.now(UTC),
    )
    store._write(**ids, progress=progress)
    maps = {path: path.read_bytes() for path in root.glob("courses/*/*/canvas/lectures/*/*.json")}
    before = store._path(**ids).read_bytes()

    dry = migration()(root, apply=False)
    assert len(dry["updated"]) == 1
    assert store._path(**ids).read_bytes() == before

    applied = migration()(root, apply=True)
    assert applied["updated"] == dry["updated"]
    current = store.read(**ids)
    assert current.delayed_reviews == {}
    assert current.pending_check is None
    assert current.goal_evidence[key].independent
    assert not current.goal_evidence[key].delayed
    assert current.turns == progress.turns
    assert all(path.read_bytes() == content for path, content in maps.items())
    assert migration()(root, apply=True)["updated"] == []


def test_migration_preserves_reviewed_tasks_and_generic_immediate_attempts(tmp_path):
    client, gate, ids, _ = setup(tmp_path)
    root = client.app.state.canvas_workspace.workspace_root
    store = CoachingProgressStore(client.app.state.canvas_workspace.layout)
    store.bind_inline_checkpoint(**ids, gate=gate)
    learning_map = client.app.state.canvas_workspace.course_canvas_store.learning_map(
        course_id=ids["course_id"], lecture_id=ids["lecture_id"]
    )
    reviewed = next(item for item in learning_map.gates if item.practice_target_id)
    progress = store.read(**ids)
    from lecturepilot.learner.coaching_episode import schedule_delayed_review

    schedule_delayed_review(
        progress,
        gate_id=reviewed.id,
        gate_revision=reviewed.revision,
        section_id=reviewed.section_id,
        transfer_prompt=reviewed.transfer_prompt,
        review_after_days=reviewed.review_after_days,
        now=datetime.now(UTC),
    )
    store._write(**ids, progress=progress)
    before = json.loads(store._path(**ids).read_text())

    assert migration()(root, apply=True)["updated"] == []
    assert json.loads(store._path(**ids).read_text()) == before
