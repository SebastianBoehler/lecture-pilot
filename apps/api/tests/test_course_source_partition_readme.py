from datetime import date

from lecturepilot.course_source_partition import select_lecture_source_files
from lecturepilot.models import Lecture
from lecturepilot.source_bundle import SourceBundleFile


def _file(path: str, kind: str = "markdown") -> SourceBundleFile:
    return SourceBundleFile(path=path, kind=kind, size_bytes=1)


def _lecture(number: int, material_path: str) -> Lecture:
    return Lecture(
        id=f"lecture-{number:02d}",
        course_id="nlp",
        title=f"Lecture {number}",
        date=date(2026, 7, number),
        material_path=material_path,
    )


def test_nested_readme_is_not_course_wide_but_stays_with_its_assigned_folder() -> None:
    lectures = [
        _lecture(1, "uploads/1_intro.pdf"),
        _lecture(2, "uploads/2_preprocessing.pdf"),
        _lecture(14, "uploads/exam-review/lecture-14/guide.md"),
    ]
    files = [
        _file("uploads/1_intro.pdf", "pdf"),
        _file("uploads/2_preprocessing.pdf", "pdf"),
        _file("uploads/README.md"),
        _file("uploads/exam-review/lecture-14/guide.md"),
        _file("uploads/exam-review/lecture-14/README.md"),
        _file("uploads/exam-review/lecture-14/protocol.txt", "text"),
    ]

    first = select_lecture_source_files(files=files, lectures=lectures, lecture_id="lecture-01")
    review = select_lecture_source_files(files=files, lectures=lectures, lecture_id="lecture-14")

    assert [item.path for item in first] == ["uploads/1_intro.pdf", "uploads/README.md"]
    assert [item.path for item in review] == [
        "uploads/README.md",
        "uploads/exam-review/lecture-14/guide.md",
        "uploads/exam-review/lecture-14/README.md",
        "uploads/exam-review/lecture-14/protocol.txt",
    ]
