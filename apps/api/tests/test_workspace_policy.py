import pytest

from lecturepilot.core.workspace import WorkspacePolicy, WorkspacePolicyError


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
