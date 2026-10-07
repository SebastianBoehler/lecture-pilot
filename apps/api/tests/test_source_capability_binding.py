import json

import pytest

from lecturepilot.agent_tool_executor import AgentToolExecutor
from source_capability_test_helpers import published_source_workspace


def _executor(workspace):
    return AgentToolExecutor(
        canvas_workspace=workspace,
        course_id="course-a",
        lecture_id="lecture-open",
        user_id="student",
    )


@pytest.mark.parametrize("new_executor", [False, True])
def test_changed_allowed_source_bytes_are_never_returned(tmp_path, new_executor):
    workspace = published_source_workspace(tmp_path)
    executor = _executor(workspace)
    source = workspace.layout.course_uploads_dir("course-a") / "current.md"
    source.write_text("Future lecture leaked under an old approved filename")
    if new_executor:
        executor = _executor(workspace)
    for tool, args in (
        ("read", {"path": "/course/source/uploads/current.md"}),
        ("grep", {"path": "/course/source/uploads", "pattern": "Future"}),
    ):
        result = executor.execute(tool, args)
        assert not result["ok"]
        assert "Future lecture leaked" not in str(result)


@pytest.mark.parametrize("new_executor", [False, True])
def test_expanded_draft_manifest_cannot_use_old_publication(tmp_path, new_executor):
    workspace = published_source_workspace(tmp_path)
    executor = _executor(workspace)
    path = workspace.layout.lecture_source_manifest_path("course-a", "lecture-open")
    manifest = json.loads(path.read_text())
    index = json.loads(workspace.layout.course_source_index_path("course-a").read_text())
    future = next(item for item in index["files"] if item["path"] == "future.md")
    manifest["files"].append({"path": future["path"], "sha256": future["sha256"]})
    path.write_text(json.dumps(manifest))
    if new_executor:
        executor = _executor(workspace)
    for tool, args in (
        ("read", {"path": "/course/source/uploads/current.md"}),
        ("read", {"path": "/course/source/uploads/future.md"}),
        ("ls", {"path": "/course/source/uploads"}),
        ("find", {"path": "/course/source/uploads"}),
    ):
        assert not executor.execute(tool, args)["ok"]


@pytest.mark.parametrize("change", ["unconfirmed", "invalid", "missing"])
def test_source_state_changes_revoke_existing_capability(tmp_path, change):
    workspace = published_source_workspace(tmp_path)
    executor = _executor(workspace)
    routing_path = workspace.layout.course_source_routing_path("course-a")
    if change == "missing":
        routing_path.unlink()
    elif change == "invalid":
        routing_path.write_text("{}")
    else:
        routing = json.loads(routing_path.read_text())
        routing["confirmed"] = False
        routing_path.write_text(json.dumps(routing))
    for current in (executor, _executor(workspace)):
        for tool, args in (
            ("read", {"path": "/course/source/uploads/current.md"}),
            ("ls", {"path": "/course/source/uploads"}),
        ):
            assert not current.execute(tool, args)["ok"]
