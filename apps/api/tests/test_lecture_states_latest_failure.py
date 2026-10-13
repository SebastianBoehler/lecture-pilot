"""A failed attempt after a usable draft or publication keeps it and still reports why."""

from datetime import UTC, datetime, timedelta
import json
import os

from test_lecture_states import _states, _workspace, _write_job, _write_sources
from test_practice_design_canvas_binding import _approved_design, _document
from test_practice_design_publication import _published_workspace


def _lecture(workspace) -> tuple:
    item = _states(workspace)["lectures"][0]
    return item["draft"], item["draft_error"], item["next_action"]


def test_a_failed_change_after_publication_keeps_the_publication_and_reports_why(tmp_path):
    _write_sources(tmp_path)
    workspace, _design = _published_workspace(tmp_path)
    assert _lecture(workspace) == ("published", None, "none")

    _write_job(workspace, status="failed", detail="/draft/topic.md: Change could not be applied.")

    assert _lecture(workspace) == ("published", "Change could not be applied.", "none")


def test_a_failure_older_than_the_publication_is_not_reported(tmp_path):
    _write_sources(tmp_path)
    workspace, _design = _published_workspace(tmp_path)
    path = _write_job(workspace, status="failed", detail="Old failure.")
    record = json.loads(path.read_text())
    record["updated_at"] = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    path.write_text(json.dumps(record))

    assert _lecture(workspace) == ("published", None, "none")


def test_a_failed_attempt_after_a_ready_draft_keeps_the_draft_reviewable(tmp_path):
    _write_sources(tmp_path)
    workspace = _workspace(tmp_path)
    design = _approved_design(workspace)
    completed = _write_job(workspace, status="completed")
    workspace.write_course_canvas_draft(
        _document(design), expected_source_revision=design.source_revision, practice_design=design
    )
    assert _lecture(workspace) == ("ready", None, "review_draft")

    failed = completed.with_name(f"{'c' * 64}.json")
    _write_job(workspace, status="failed", path=failed, detail="The change failed.")
    os.utime(failed, ns=(completed.stat().st_mtime_ns + 10**9,) * 2)

    assert _lecture(workspace) == ("ready", "The change failed.", "review_draft")
