from __future__ import annotations

import json
from pathlib import Path
import re
import shutil

from lecturepilot.durable_files import atomic_write_json, fsync_directory
from lecturepilot.practice_exam_models import PracticeExam
from lecturepilot.storage_layout import StorageLayout


_EXAM_ID = re.compile(r"^[0-9a-f]{32}$")


class PracticeExamStore:
    def __init__(self, layout: StorageLayout) -> None:
        self.layout = layout

    def write(self, *, user_id: str, course_id: str, exam: PracticeExam) -> PracticeExam:
        if exam.course_id != course_id:
            raise ValueError("Practice exam does not belong to the selected course.")
        root = self.layout.practice_exam_dir(user_id, course_id, exam.id)
        if root.exists():
            raise FileExistsError(exam.id)
        atomic_write_json(root / "exam.json", exam.model_dump(mode="json"))
        return exam

    def read(self, *, user_id: str, course_id: str, exam_id: str) -> PracticeExam:
        path = self._exam_path(user_id, course_id, exam_id)
        if not path.is_file():
            raise FileNotFoundError(exam_id)
        return PracticeExam.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def list(self, *, user_id: str, course_id: str) -> list[PracticeExam]:
        root = self.layout.practice_exams_dir(user_id, course_id)
        if not root.exists():
            return []
        exams = [
            PracticeExam.model_validate(json.loads(path.read_text(encoding="utf-8")))
            for path in root.glob("*/exam.json")
            if path.is_file()
        ]
        return sorted(exams, key=lambda exam: (exam.created_at, exam.id), reverse=True)

    def delete(self, *, user_id: str, course_id: str, exam_id: str) -> bool:
        root = self._exam_path(user_id, course_id, exam_id).parent
        if not root.exists():
            return False
        shutil.rmtree(root)
        fsync_directory(root.parent)
        return True

    def pdf_path(self, *, user_id: str, course_id: str, exam_id: str) -> Path:
        return self._exam_path(user_id, course_id, exam_id).parent / "exam.pdf"

    def _exam_path(self, user_id: str, course_id: str, exam_id: str) -> Path:
        if _EXAM_ID.fullmatch(exam_id) is None:
            raise FileNotFoundError(exam_id)
        return self.layout.practice_exam_dir(user_id, course_id, exam_id) / "exam.json"
