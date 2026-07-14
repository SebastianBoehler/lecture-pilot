from __future__ import annotations

from io import BytesIO
from pathlib import Path
import stat
import zipfile

import pytest

from lecturepilot_latex_compiler.archive import extract_source_archive
from lecturepilot_latex_compiler.errors import CompilerServiceError


def _write_zip(path: Path, files: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)


def test_extracts_regular_source_tree(tmp_path: Path) -> None:
    archive = tmp_path / "source.zip"
    _write_zip(archive, {"slides/main.tex": b"content", "slides/images/a.png": b"png"})

    destination = tmp_path / "source"
    extract_source_archive(archive, destination)

    assert (destination / "slides/main.tex").read_bytes() == b"content"
    assert (destination / "slides/images/a.png").read_bytes() == b"png"


@pytest.mark.parametrize("name", ["../escape.tex", "/absolute.tex", ".hidden/main.tex"])
def test_rejects_unsafe_paths(tmp_path: Path, name: str) -> None:
    archive = tmp_path / "source.zip"
    _write_zip(archive, {name: b"content"})

    with pytest.raises(CompilerServiceError, match="invalid"):
        extract_source_archive(archive, tmp_path / "source")


def test_rejects_symbolic_links(tmp_path: Path) -> None:
    archive = tmp_path / "source.zip"
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as payload:
        link = zipfile.ZipInfo("link.tex")
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        payload.writestr(link, "target.tex")
    archive.write_bytes(buffer.getvalue())

    with pytest.raises(CompilerServiceError, match="invalid"):
        extract_source_archive(archive, tmp_path / "source")
