from lecturepilot.storage_layout import StorageLayout
from lecturepilot.user_memory import UserMemoryStore


def test_user_memory_context_includes_global_and_course_memory(tmp_path) -> None:
    layout = StorageLayout(tmp_path)
    store = UserMemoryStore(layout)

    context = store.read_context("student01", "martius-ml")

    user_root = layout.user_root("student01")
    assert context.global_notes == ""
    assert context.course_notes == ""
    assert context.preferences == {}
    assert (user_root / "memories" / "global.md").exists()
    assert (user_root / "memories" / "preferences.json").exists()
    assert (user_root / "memories" / "memory-trace.jsonl").exists()
    assert (user_root / "courses" / "martius-ml" / "memories" / "course.md").exists()
    assert (user_root / "courses" / "martius-ml" / "memories" / "memory-trace.jsonl").exists()

    (user_root / "memories" / "global.md").write_text(
        "- prefers concise analogies\n", encoding="utf-8"
    )
    (user_root / "courses" / "martius-ml" / "memories" / "course.md").write_text(
        "- needs Bayes risk examples\n",
        encoding="utf-8",
    )

    context = store.read_context("student01", "martius-ml")

    assert "concise analogies" in context.global_notes
    assert "Bayes risk examples" in context.course_notes
