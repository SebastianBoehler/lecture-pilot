import json

from fastapi.testclient import TestClient

from lecturepilot.app import create_app
from lecturepilot.storage_layout import StorageLayout
from lecturepilot.user_memory import UserMemoryStore

from auth_helpers import professor_headers, student_headers


def test_learner_profile_persists_goal_and_lists_owned_course_files(tmp_path) -> None:
    app = create_app()
    layout = StorageLayout(tmp_path)
    app.state.user_memory_store = UserMemoryStore(layout)
    lecture_root = layout.user_lecture_root("student01", "martius-ml", "lecture-01")
    lecture_root.mkdir(parents=True)
    (lecture_root / "gates.json").write_text(
        json.dumps({"gates": {"outcome": {"status": "passed"}}}),
        encoding="utf-8",
    )
    note_path = lecture_root / "canvas" / "student" / "summary.md"
    note_path.parent.mkdir(parents=True)
    note_path.write_text("# My summary\n", encoding="utf-8")

    with TestClient(app) as client:
        saved = client.post(
            "/me/learning-profile",
            headers=student_headers(),
            json={"learning_goal": "understand_deeply", "onboarding_completed": True},
        )
        assert saved.status_code == 200

        response = client.get("/me/learning-profile", headers=student_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["learning_goal"] == "understand_deeply"
    assert payload["onboarding_completed"] is True
    assert payload["preferences"]["learning_goal"] == "understand_deeply"
    course = next(item for item in payload["courses"] if item["course_id"] == "martius-ml")
    assert course["passed_lecture_ids"] == ["lecture-01"]
    files = {item["path"]: item for item in course["files"]}
    assert files["lectures/lecture-01/canvas/student/summary.md"]["content"] == "# My summary\n"
    assert "users/" not in " ".join(files)


def test_learner_can_remove_preferences_and_clear_only_selected_memory(tmp_path) -> None:
    app = create_app()
    layout = StorageLayout(tmp_path)
    store = UserMemoryStore(layout)
    app.state.user_memory_store = store
    store.remember(
        user_id="student01",
        course_id="martius-ml",
        lecture_id="lecture-01",
        note="Use concise explanations",
        scope="global",
        preference_key="analogy",
        preference_value="football",
    )
    store.remember(
        user_id="student01",
        course_id="martius-ml",
        lecture_id="lecture-01",
        note="Needs more Bayes examples",
        scope="course",
    )

    with TestClient(app) as client:
        removed = client.delete(
            "/me/learning-profile/preferences/analogy",
            headers=student_headers(),
        )
        cleared = client.delete(
            "/me/learning-profile/memory?course_id=martius-ml",
            headers=student_headers(),
        )
        profile = client.get("/me/learning-profile", headers=student_headers())

    assert removed.status_code == 204
    assert cleared.status_code == 204
    assert "analogy" not in profile.json()["preferences"]
    assert "concise explanations" in profile.json()["global_notes"]
    course = next(item for item in profile.json()["courses"] if item["course_id"] == "martius-ml")
    assert course["memory"] == ""
    assert (layout.user_memories_dir("student01") / "memory-trace.jsonl").read_text()
    assert (
        layout.user_course_memories_dir("student01", "martius-ml") / "memory-trace.jsonl"
    ).read_text() == ""


def test_learner_profile_rejects_non_students(tmp_path) -> None:
    app = create_app()
    app.state.user_memory_store = UserMemoryStore(StorageLayout(tmp_path))

    with TestClient(app) as client:
        response = client.get("/me/learning-profile", headers=professor_headers())

    assert response.status_code == 403
