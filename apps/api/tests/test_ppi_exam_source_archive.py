from __future__ import annotations

from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import fitz
import pytest

from lecturepilot.ppi_exam_source_archive import PpiArchiveError, normalize_ppi_archive


def test_archive_normalizes_valid_pdf_text_and_markdown(tmp_path: Path) -> None:
    files = normalize_ppi_archive(
        _zip(
            {
                "exam.pdf": _pdf("What is Bayes risk?"),
                "notes/questions.txt": b"Kernel trick?",
                "README.md": b"# Exam protocols\n\nExaminer metadata",
            }
        ),
        output_root=tmp_path,
    )

    assert [item.path for item in files] == ["exam.pdf", "notes/questions.txt", "README.md"]
    assert [item.media_type for item in files] == [
        "application/pdf",
        "text/plain",
        "text/markdown",
    ]
    assert all(len(item.sha256) == 64 for item in files)
    assert "Bayes risk" in (tmp_path / files[0].text_path).read_text(encoding="utf-8")
    assert "Kernel trick" in (tmp_path / files[1].text_path).read_text(encoding="utf-8")
    assert "Examiner metadata" in (tmp_path / files[2].text_path).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("path", "message"),
    [
        ("../stolen.txt", "unsafe path"),
        ("/absolute.txt", "unsafe path"),
        (".hidden.txt", "hidden path"),
        ("folder/.hidden.txt", "hidden path"),
        ("questions.exe", "unsupported file"),
    ],
)
def test_archive_rejects_unsafe_members(path: str, message: str, tmp_path: Path) -> None:
    with pytest.raises(PpiArchiveError, match=message):
        normalize_ppi_archive(_zip({path: b"question"}), output_root=tmp_path)
    assert not list(tmp_path.iterdir())


def test_archive_rejects_symlink(tmp_path: Path) -> None:
    archive = BytesIO()
    with ZipFile(archive, "w") as bundle:
        info = ZipInfo("link.txt")
        info.create_system = 3
        info.external_attr = 0o120777 << 16
        bundle.writestr(info, "target")

    with pytest.raises(PpiArchiveError, match="symbolic link"):
        normalize_ppi_archive(archive.getvalue(), output_root=tmp_path)


def test_archive_rejects_duplicate_normalized_paths(tmp_path: Path) -> None:
    archive = BytesIO()
    with ZipFile(archive, "w") as bundle:
        bundle.writestr("Questions.txt", "first")
        bundle.writestr("questions.txt", "second")

    with pytest.raises(PpiArchiveError, match="duplicate path"):
        normalize_ppi_archive(archive.getvalue(), output_root=tmp_path)


def test_archive_rejects_file_count_limit(tmp_path: Path) -> None:
    with pytest.raises(PpiArchiveError, match="too many files"):
        normalize_ppi_archive(
            _zip({"one.txt": b"1", "two.txt": b"2"}),
            output_root=tmp_path,
            max_files=1,
        )


def test_archive_rejects_compressed_and_expanded_size_limits(tmp_path: Path) -> None:
    archive = _zip({"large.txt": b"x" * 512})
    with pytest.raises(PpiArchiveError, match="compressed size"):
        normalize_ppi_archive(archive, output_root=tmp_path, max_compressed_bytes=1)
    with pytest.raises(PpiArchiveError, match="expanded size"):
        normalize_ppi_archive(archive, output_root=tmp_path, max_expanded_bytes=100)


def test_archive_rejects_malformed_pdf_and_cleans_output(tmp_path: Path) -> None:
    with pytest.raises(PpiArchiveError, match="invalid PDF"):
        normalize_ppi_archive(_zip({"bad.pdf": b"not a pdf"}), output_root=tmp_path)

    assert not list(tmp_path.iterdir())


def _zip(files: dict[str, bytes]) -> bytes:
    archive = BytesIO()
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as bundle:
        for path, content in files.items():
            bundle.writestr(path, content)
    return archive.getvalue()


def _pdf(text: str) -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    content = document.tobytes()
    document.close()
    return content
