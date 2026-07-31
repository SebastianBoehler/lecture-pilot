from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from lecturepilot.ppi_exam_source_store import PpiExamSourceStore
from lecturepilot.storage_layout import StorageLayout


def test_generation_reads_only_a_bounded_protocol_excerpt(tmp_path: Path) -> None:
    store = PpiExamSourceStore(StorageLayout(tmp_path))
    store.import_archive(
        user_id="student-a",
        course_id="ml",
        lecture_id=42,
        title="Machine Learning",
        protocol_count=1,
        filename="protocols.zip",
        archive=_archive("0123456789" * 20),
    )

    texts = store.normalized_text(
        user_id="student-a",
        course_id="ml",
        source_id="ppi-42",
        max_characters=17,
    )

    assert texts == [("protocol.txt", "01234567890123456")]


def _archive(text: str) -> bytes:
    content = BytesIO()
    with ZipFile(content, "w") as bundle:
        bundle.writestr("protocol.txt", text)
    return content.getvalue()
