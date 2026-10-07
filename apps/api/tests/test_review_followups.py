from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from lecturepilot.agent_side_effect_tools import _explicit_memory_request
from lecturepilot.authoring_limits import AuthoringBudgetExceeded
from lecturepilot.model_usage import complete_with_usage
from lecturepilot.model_usage_total import model_usage_total
from lecturepilot.readiness_progress import ReadinessProgressStore
from lecturepilot.review_queue_order import interleave_lectures
from lecturepilot.storage_layout import StorageLayout
from test_source_capability_binding import _executor
from source_capability_test_helpers import published_source_workspace


@pytest.mark.parametrize(
    "args",
    [
        {"path": "/course/source/uploads/current.md", "max_chars": 10**8},
        {"path": "/course/source/uploads/current.md", "max_chars": True},
        {"path": "/course/source/uploads/current.md", "unexpected": "value"},
    ],
)
def test_tool_arguments_are_checked_before_filesystem_access(tmp_path, args):
    executor = _executor(published_source_workspace(tmp_path))
    result = executor.execute("read", args)
    assert not result["ok"]
    assert "content" not in result


def test_edit_requires_one_unique_match(tmp_path):
    executor = _executor(published_source_workspace(tmp_path))
    path = executor.canvas_workspace.layout.user_canvas_dir("student", "course-a", "lecture-open")
    file = path / "student" / "note.md"
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(
        "---\nid: note\ntitle: Note\nsource_ref: student workspace\n---\n\nRepeated phrase. Repeated phrase."
    )
    result = executor.execute(
        "edit",
        {
            "path": "/lecture/canvas/student/note.md",
            "old_text": "Repeated phrase.",
            "new_text": "Changed.",
        },
    )
    assert not result["ok"]
    assert file.read_text().count("Repeated phrase.") == 2


@pytest.mark.parametrize("name", ["LEARNING-MAP.json", "Learning-Map.JSON"])
def test_hidden_map_is_excluded_regardless_of_filesystem_case(tmp_path, name):
    executor = _executor(published_source_workspace(tmp_path))
    assert not executor.execute("read", {"path": f"/course/canvas/{name}"})["ok"]


def test_review_interleaving_preserves_global_due_order():
    now = datetime.now(UTC)
    items = [
        SimpleNamespace(lecture_id=lecture, due_at=(now + timedelta(days=days)).isoformat())
        for lecture, days in [("a", 1), ("a", 2), ("b", 50)]
    ]
    assert [item.due_at for item in interleave_lectures(items)] == sorted(
        item.due_at for item in items
    )


def test_corrupt_readiness_progress_is_preserved_and_reported(tmp_path):
    store = ReadinessProgressStore(StorageLayout(tmp_path))
    path = store._path(user_id="student", course_id="course")
    path.parent.mkdir(parents=True)
    path.write_text('{"attempts":')
    with pytest.raises(ValueError, match="progress"):
        store.read(user_id="student", course_id="course")
    assert path.read_text() == '{"attempts":'


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Speichere bitte, dass ich langsam lerne.", True),
        ("Merk dir bitte, dass ich Metaphern nicht mag.", True),
        ("Remember the formula from lecture 2?", False),
        ("Please don't remember this preference.", False),
        ("Speichere bitte nicht diese Präferenz.", False),
        ("Bitte merke dir, dass ich Beispiele bevorzuge.", True),
    ],
)
def test_memory_consent_distinguishes_commands_from_content(text, expected):
    assert _explicit_memory_request(text) is expected


async def test_budget_refusal_before_dispatch_neither_spends_nor_records_provider_failure():
    calls = []
    recorder = SimpleNamespace(record_failure=lambda **kwargs: calls.append(kwargs))

    def refuse():
        raise AuthoringBudgetExceeded("budget")

    async def completion(**kwargs):
        raise AssertionError("Provider must not be called")

    with model_usage_total() as total:
        with pytest.raises(AuthoringBudgetExceeded):
            await complete_with_usage(
                recorder, completion, model="openai/test", before_request=refuse
            )
        assert total.total_tokens == 0
    assert not calls
