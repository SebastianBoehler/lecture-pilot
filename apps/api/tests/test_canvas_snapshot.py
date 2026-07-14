from pathlib import Path

import pytest

from lecturepilot import canvas_snapshot
from lecturepilot.canvas_snapshot import locked_canvas_paths, replace_canvas_snapshot


def test_failed_snapshot_swap_restores_previous_directory(
    tmp_path: Path,
    monkeypatch,
) -> None:
    target = tmp_path / "canvas"
    target.mkdir()
    (target / "marker.txt").write_text("previous", encoding="utf-8")
    original_replace = canvas_snapshot.os.replace

    def fail_staging_commit(source, destination) -> None:
        if Path(source).name.startswith(".canvas.staging-") and Path(destination) == target:
            raise OSError("injected swap failure")
        original_replace(source, destination)

    monkeypatch.setattr(canvas_snapshot.os, "replace", fail_staging_commit)

    with locked_canvas_paths(target):
        with pytest.raises(OSError, match="injected swap failure"):
            replace_canvas_snapshot(target, _build_replacement)

    assert (target / "marker.txt").read_text(encoding="utf-8") == "previous"


def test_lock_recovers_previous_directory_after_interrupted_swap(tmp_path: Path) -> None:
    target = tmp_path / "canvas"
    previous = tmp_path / ".canvas.previous-interrupted"
    staging = tmp_path / ".canvas.staging-interrupted"
    previous.mkdir()
    staging.mkdir()
    (previous / "marker.txt").write_text("previous", encoding="utf-8")
    (staging / "marker.txt").write_text("partial", encoding="utf-8")

    with locked_canvas_paths(target):
        assert (target / "marker.txt").read_text(encoding="utf-8") == "previous"

    assert not previous.exists()
    assert not staging.exists()


def _build_replacement(staging: Path) -> None:
    (staging / "marker.txt").write_text("replacement", encoding="utf-8")
