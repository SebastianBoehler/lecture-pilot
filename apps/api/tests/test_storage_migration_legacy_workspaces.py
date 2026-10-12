from pathlib import Path

from lecturepilot.storage_layout import StorageLayout
from lecturepilot.storage_migration_legacy_workspaces import migrate


def _seed(tmp_path: Path) -> tuple[Path, Path, Path]:
    layout = StorageLayout(tmp_path)
    legacy = tmp_path / "workspaces" / "students" / layout.user_key("u1") / "courses" / "c1"
    (legacy / "lectures" / "l1").mkdir(parents=True)
    (legacy / "lectures" / "l1" / "canvas.json").write_text("{}", encoding="utf-8")
    (legacy / "progress.json").write_text("{}", encoding="utf-8")
    lecture = layout.user_lecture_root("u1", "c1", "l1")
    lecture.mkdir(parents=True)
    stale = lecture / "canvas.json"
    stale.write_text("{}", encoding="utf-8")
    kept = lecture / "gates.json"
    kept.write_text("{}", encoding="utf-8")
    preview = layout.user_lecture_root("professor-preview:p1", "c1", "l1")
    preview.mkdir(parents=True)
    (preview / "canvas.json").write_text("{}", encoding="utf-8")
    return stale, kept, preview / "canvas.json"


def test_dry_run_reports_orphaned_legacy_learner_data(tmp_path: Path) -> None:
    stale, kept, preview_stale = _seed(tmp_path)

    report = migrate(tmp_path, apply=False)

    assert report["applied"] is False
    assert report["legacy_root"] == "workspaces/students"
    assert report["legacy_root_files"] == 2
    assert sorted(report["stale_canvas_json"]) == sorted(
        str(path.relative_to(tmp_path)) for path in (stale, preview_stale)
    )
    assert (tmp_path / "workspaces" / "students").exists()
    assert stale.exists()


def test_apply_removes_legacy_root_and_stale_compiled_canvases_only(tmp_path: Path) -> None:
    stale, kept, preview_stale = _seed(tmp_path)

    migrate(tmp_path, apply=True)

    assert not (tmp_path / "workspaces").exists()
    assert not stale.exists() and not preview_stale.exists()
    assert kept.exists()
    again = migrate(tmp_path, apply=True)
    assert again["legacy_root"] is None
    assert again["legacy_root_files"] == 0
    assert again["stale_canvas_json"] == []
