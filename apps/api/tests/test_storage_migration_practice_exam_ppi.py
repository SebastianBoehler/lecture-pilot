import json
from pathlib import Path

from lecturepilot.core.storage_layout import StorageLayout
from lecturepilot.exams.practice_exam_models import PracticeExam
from lecturepilot.migrations_storage.storage_migration_practice_exam_ppi import migrate
from test_practice_exam_store import _exam


def test_strips_retired_ppi_fields_so_stored_exams_load_again(tmp_path: Path) -> None:
    exam = _exam().model_dump(mode="json")
    exam["ppi_source_ids"] = ["ppi-42"]
    for question in exam["questions"]:
        question["ppi_pattern_ids"] = ["ppi-42"]
    path = StorageLayout(tmp_path).practice_exam_dir("student-a", "ml", exam["id"]) / "exam.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(exam), encoding="utf-8")
    before = path.read_bytes()

    dry_run = migrate(tmp_path)

    assert dry_run["changed_files"] == [str(path.relative_to(tmp_path))]
    assert path.read_bytes() == before

    migrate(tmp_path, apply=True)

    migrated = PracticeExam.model_validate_json(path.read_text(encoding="utf-8"))
    assert migrated == _exam()
    assert migrate(tmp_path, apply=True)["changed_files"] == []
