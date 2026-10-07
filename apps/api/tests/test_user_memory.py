from lecturepilot.storage_layout import StorageLayout
from lecturepilot.user_memory import UserMemoryStore
import pytest
from lecturepilot.agent_side_effect_tools import _explicit_memory_request


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


def test_memory_context_keeps_recent_notes_after_the_character_limit(tmp_path):
    store = UserMemoryStore(StorageLayout(tmp_path))
    store.read_context("u1", "course")
    for scope in ("global", "course"):
        store.remember(
            user_id="u1",
            course_id="course",
            lecture_id="lecture",
            note="Older note " * 500,
            scope=scope,
        )
        store.remember(
            user_id="u1",
            course_id="course",
            lecture_id="lecture",
            note="Newest instruction",
            scope=scope,
        )
    context = store.read_context("u1", "course")
    assert "Newest instruction" in context.global_notes
    assert "Newest instruction" in context.course_notes
    assert len(context.global_notes) <= 4000


@pytest.mark.parametrize("key", ["onboarding_completed", "learning_goal", "unknown"])
def test_model_memory_cannot_change_profile_control_fields(tmp_path, key):
    store = UserMemoryStore(StorageLayout(tmp_path))
    with pytest.raises(ValueError, match="preference"):
        store.remember(
            user_id="u1",
            course_id="course",
            lecture_id="lecture",
            note="Do not partially save this",
            preference_key=key,
            preference_value="false",
        )
    assert store.read_context("u1").global_notes == ""


@pytest.mark.parametrize(
    "message,allowed",
    [
        ("I don't remember Bayes' rule", False),
        ("I cannot remember the formula", False),
        ("Do not remember this", False),
        ("Don't save this preference", False),
        ("Merk dir bitte: kurze Beispiele", True),
        ("Merke dir, dass ich Deutsch bevorzuge", True),
        ("Bitte merk dir das nicht", False),
        ("Remember that I prefer examples", True),
        ("Please remember this preference", True),
    ],
)
def test_memory_requires_an_affirmative_request(message, allowed):
    assert _explicit_memory_request(message) is allowed
