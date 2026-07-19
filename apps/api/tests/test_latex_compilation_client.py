from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pytest

from lecturepilot.latex_compilation_client import (
    COMPILATION_PROTOCOL_VERSION,
    LatexCompilationError,
    compile_latex_deck,
)
from lecturepilot.source_index_models import CourseSourceIndex, IndexedSourceFile


def test_cache_protocol_identifies_tectonic_engine_and_bundle() -> None:
    assert "tectonic-0.16.9" in COMPILATION_PROTOCOL_VERSION
    assert "tlextras-2022.0r0" in COMPILATION_PROTOCOL_VERSION


def test_compiler_bundle_contains_tex_dependencies_but_not_video(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "uploads"
    _write(root / "Lecture02.tex", "\\documentclass{beamer}\\begin{document}x\\end{document}")
    _write(root / "header.tex", "\\newcommand{\\course}{ML}")
    _write(root / "theme.sty", "\\ProvidesPackage{theme}")
    _write(root / "images" / "plot.png", "image")
    _write(root / "walkthrough.mp4", "video")
    index = _index(root)
    captured: dict[str, bytes | str] = {}

    def compile_request(archive, size: int, main_path: str) -> bytes:
        captured["archive"] = archive.read(size)
        captured["main_path"] = main_path
        return _pdf_bytes("compiled")

    monkeypatch.setattr(
        "lecturepilot.latex_compilation_client._request_compilation", compile_request
    )

    output = compile_latex_deck(
        source_root=root,
        inputs=[item for item in index.files if item.kind != "video"],
        source_path="Lecture02.tex",
        output_root=tmp_path / "normalized",
        lecture_id="lecture-02",
    )

    with ZipFile(BytesIO(captured["archive"])) as archive:
        assert set(archive.namelist()) == {
            "Lecture02.tex",
            "header.tex",
            "images/plot.png",
            "theme.sty",
        }
    assert captured["main_path"] == "Lecture02.tex"
    assert output.read_bytes().startswith(b"%PDF")


def test_compiled_pdf_cache_changes_when_a_dependency_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "uploads"
    _write(root / "Lecture02.tex", "lecture")
    _write(root / "macros.tex", "version one")
    calls = 0

    def compile_request(archive, size: int, main_path: str) -> bytes:
        nonlocal calls
        calls += 1
        return _pdf_bytes(f"compiled {calls}")

    monkeypatch.setattr(
        "lecturepilot.latex_compilation_client._request_compilation", compile_request
    )
    first_index = _index(root)
    first = compile_latex_deck(
        source_root=root,
        inputs=first_index.files,
        source_path="Lecture02.tex",
        output_root=tmp_path / "normalized",
        lecture_id="lecture-02",
    )
    cached = compile_latex_deck(
        source_root=root,
        inputs=first_index.files,
        source_path="Lecture02.tex",
        output_root=tmp_path / "normalized",
        lecture_id="lecture-02",
    )
    _write(root / "macros.tex", "version two")
    changed_index = _index(root)
    changed = compile_latex_deck(
        source_root=root,
        inputs=changed_index.files,
        source_path="Lecture02.tex",
        output_root=tmp_path / "normalized",
        lecture_id="lecture-02",
    )

    assert first == cached
    assert changed != first
    assert calls == 2


def test_invalid_compiler_response_is_rejected_without_writing_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "uploads"
    _write(root / "Lecture02.tex", "lecture")
    monkeypatch.setattr(
        "lecturepilot.latex_compilation_client._request_compilation",
        lambda archive, size, main_path: b"not a pdf",
    )

    with pytest.raises(LatexCompilationError, match="valid PDF"):
        compile_latex_deck(
            source_root=root,
            inputs=_index(root).files,
            source_path="Lecture02.tex",
            output_root=tmp_path / "normalized",
            lecture_id="lecture-02",
        )

    assert not list((tmp_path / "normalized").rglob("*.pdf"))


def test_source_mutation_after_indexing_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "uploads"
    source = root / "Lecture02.tex"
    _write(source, "version one")
    index = _index(root)
    _write(source, "version two")
    monkeypatch.setattr(
        "lecturepilot.latex_compilation_client._request_compilation",
        lambda archive, size, main_path: _pdf_bytes("unreachable"),
    )

    with pytest.raises(LatexCompilationError, match="changed during compilation") as error:
        compile_latex_deck(
            source_root=root,
            inputs=index.files,
            source_path="Lecture02.tex",
            output_root=tmp_path / "normalized",
            lecture_id="lecture-02",
        )

    assert error.value.code == "source_changed"


def test_cached_pdf_is_not_reused_after_unindexed_source_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "uploads"
    source = root / "Lecture02.tex"
    _write(source, "version one")
    index = _index(root)
    monkeypatch.setattr(
        "lecturepilot.latex_compilation_client._request_compilation",
        lambda archive, size, main_path: _pdf_bytes("compiled"),
    )
    compile_latex_deck(
        source_root=root,
        inputs=index.files,
        source_path="Lecture02.tex",
        output_root=tmp_path / "normalized",
        lecture_id="lecture-02",
    )
    _write(source, "version two")

    with pytest.raises(LatexCompilationError, match="changed during compilation"):
        compile_latex_deck(
            source_root=root,
            inputs=index.files,
            source_path="Lecture02.tex",
            output_root=tmp_path / "normalized",
            lecture_id="lecture-02",
        )


def _index(root: Path) -> CourseSourceIndex:
    import hashlib

    kinds = {
        ".tex": "latex",
        ".sty": "latex-support",
        ".png": "image",
        ".mp4": "video",
    }
    files = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        payload = path.read_bytes()
        files.append(
            IndexedSourceFile(
                path=path.relative_to(root).as_posix(),
                kind=kinds[path.suffix],
                size_bytes=len(payload),
                sha256=hashlib.sha256(payload).hexdigest(),
                modified_ns=path.stat().st_mtime_ns,
            )
        )
    return CourseSourceIndex(course_id="demo-course", files=files)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _pdf_bytes(text: str) -> bytes:
    import fitz

    document = fitz.open()
    page = document.new_page(width=320, height=160)
    page.insert_text((24, 72), text)
    payload = document.tobytes()
    document.close()
    return payload
