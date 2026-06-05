from datetime import date

import pytest

from lecturepilot.models import Lecture
from lecturepilot.policies import is_lecture_unlocked
from lecturepilot.workspace import WorkspacePolicy, WorkspacePolicyError


def test_unlocks_only_lectures_on_or_before_today() -> None:
    past = Lecture(id="l1", course_id="c1", title="Past", date=date(2026, 6, 4))
    today = Lecture(id="l2", course_id="c1", title="Today", date=date(2026, 6, 5))
    future = Lecture(id="l3", course_id="c1", title="Future", date=date(2026, 6, 6))

    assert is_lecture_unlocked(past, today=date(2026, 6, 5))
    assert is_lecture_unlocked(today, today=date(2026, 6, 5))
    assert not is_lecture_unlocked(future, today=date(2026, 6, 5))


def test_workspace_policy_allows_only_typed_learning_artifacts() -> None:
    policy = WorkspacePolicy()

    checked = policy.validate_write("users/u1/course/c1/lecture/l1/summary.md", 1024)

    assert checked.kind == "markdown"
    assert checked.path == "users/u1/course/c1/lecture/l1/summary.md"


@pytest.mark.parametrize(
    ("path", "size"),
    [
        ("users/u1/course/c1/lecture/l1/run.sh", 100),
        ("users/u1/course/c1/lecture/l1/archive.zip", 100),
        ("../outside.md", 100),
        ("users/u1/course/c1/lecture/l1/large.json", 3 * 1024 * 1024),
    ],
)
def test_workspace_policy_rejects_unsafe_or_oversized_files(path: str, size: int) -> None:
    policy = WorkspacePolicy()

    with pytest.raises(WorkspacePolicyError):
        policy.validate_write(path, size)

