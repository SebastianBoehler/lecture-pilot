import json
from pathlib import Path

from lecturepilot.core.storage_layout import StorageLayout
from lecturepilot.migrations_storage.storage_migration_legacy_publications import migrate


def _publication(path: Path, payload: dict) -> None:
    path.mkdir(parents=True)
    (path / "publication.json").write_text(json.dumps(payload), encoding="utf-8")


def test_lists_legacy_publications_without_changing_them(tmp_path: Path) -> None:
    layout = StorageLayout(tmp_path)
    legacy = layout.course_canvas_dir("course-1", "lecture-01")
    _publication(legacy, {"schema_version": 1, "source_draft_path": "d", "published_path": "p"})
    _publication(
        layout.course_canvas_dir("course-1", "lecture-02"),
        {"schema_version": 1, "source_revision": "a" * 64, "draft_digest": "b" * 64},
    )
    before = (legacy / "publication.json").read_bytes()

    report = migrate(tmp_path, apply=True)

    assert report["report_only"] is True
    assert report["legacy_publications"] == [
        {"tenant": "tenant-tuebingen", "course_id": "course-1", "lecture_id": "lecture-01"}
    ]
    assert (legacy / "publication.json").read_bytes() == before
