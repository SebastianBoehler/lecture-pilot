from __future__ import annotations

import hashlib
from pathlib import Path

from lecturepilot.latex_dependency_bundle import resolve_latex_compiler_inputs
from lecturepilot.source_bundle import SOURCE_SUFFIXES
from lecturepilot.source_index_models import CourseSourceIndex, IndexedSourceFile


def test_resolver_includes_reachable_tex_theme_and_graphics_only(tmp_path: Path) -> None:
    root = tmp_path / "uploads"
    _write(
        root / "Lecture02.tex",
        r"""
        \usetheme{UniTuebingen}
        \graphicspath{{images/}}
        \input{header}
        \input{sections/detail}
        \ig{examples/plot}
        """,
    )
    _write(root / "header.tex", r"\input{macros}")
    _write(root / "macros.tex", r"\includegraphics{images/shared.pdf}")
    _write(root / "sections/detail.tex", r"\includegraphics{nested.png}")
    _write(root / "beamerthemeUniTuebingen.sty", r"\ProvidesPackage{theme}")
    _write(root / "images/examples/plot.png", "plot")
    _write(root / "images/shared.pdf", "%PDF-shared")
    _write(root / "sections/nested.png", "nested")
    _write(root / "images/unrelated.png", "unrelated")
    _write(root / "Lecture03.tex", "future lecture")
    _write(root / "walkthrough.mp4", "video")

    inputs = resolve_latex_compiler_inputs(
        source_root=root,
        source_index=_index(root),
        source_path="Lecture02.tex",
    )

    assert [item.path for item in inputs] == [
        "beamerthemeUniTuebingen.sty",
        "header.tex",
        "images/examples/plot.png",
        "images/shared.pdf",
        "Lecture02.tex",
        "macros.tex",
        "sections/detail.tex",
        "sections/nested.png",
    ]


def test_resolver_never_includes_another_scheduled_lecture(tmp_path: Path) -> None:
    root = tmp_path / "uploads"
    _write(root / "Lecture02.tex", r"\input{Lecture03}")
    _write(root / "Lecture03.tex", "future lecture")

    inputs = resolve_latex_compiler_inputs(
        source_root=root,
        source_index=_index(root),
        source_path="Lecture02.tex",
        forbidden_paths={"Lecture03.tex"},
    )

    assert [item.path for item in inputs] == ["Lecture02.tex"]


def test_dynamic_asset_reference_does_not_pull_unrelated_course_assets(tmp_path: Path) -> None:
    root = tmp_path / "uploads"
    _write(root / "Lecture02.tex", r"\includegraphics{\dynamicFigure}")
    _write(root / "images/private-future-figure.png", "future")

    inputs = resolve_latex_compiler_inputs(
        source_root=root,
        source_index=_index(root),
        source_path="Lecture02.tex",
    )

    assert [item.path for item in inputs] == ["Lecture02.tex"]


def test_simple_asset_macro_arguments_resolve_without_bundling_the_directory(
    tmp_path: Path,
) -> None:
    root = tmp_path / "uploads"
    _write(root / "Lecture02.tex", r"\input{header}\pingo{02_interactive}")
    _write(
        root / "header.tex",
        r"\newcommand{\pingo}[1]{\includegraphics{feedback/feedback_qr_#1.png}}",
    )
    _write(root / "feedback/feedback_qr_02_interactive.png", "current")
    _write(root / "feedback/feedback_qr_03_future.png", "future")

    inputs = resolve_latex_compiler_inputs(
        source_root=root,
        source_index=_index(root),
        source_path="Lecture02.tex",
    )

    assert [item.path for item in inputs] == [
        "feedback/feedback_qr_02_interactive.png",
        "header.tex",
        "Lecture02.tex",
    ]


def test_decimal_asset_basename_still_resolves_a_real_graphic_extension(tmp_path: Path) -> None:
    root = tmp_path / "uploads"
    _write(
        root / "Lecture08.tex",
        r"\graphicspath{{images/clustering/}}\ig{synthetic_blobs_0.35_data}",
    )
    _write(root / "images/clustering/synthetic_blobs_0.35_data.pdf", "%PDF-figure")

    inputs = resolve_latex_compiler_inputs(
        source_root=root,
        source_index=_index(root),
        source_path="Lecture08.tex",
    )

    assert [item.path for item in inputs] == [
        "images/clustering/synthetic_blobs_0.35_data.pdf",
        "Lecture08.tex",
    ]


def test_resolver_includes_custom_class_and_bibtex_support(tmp_path: Path) -> None:
    root = tmp_path / "uploads"
    _write(
        root / "nested/course/main.tex",
        r"""
        \documentclass{lecture-notes}
        \bibliographystyle{course-style}
        \bibliography{references}
        """,
    )
    _write(root / "lecture-notes.cls", r"\LoadClass{article}")
    _write(root / "course-style.bst", "ENTRY{}{}{}")
    _write(root / "references.bib", "@book{source, title={Course source}}")

    inputs = resolve_latex_compiler_inputs(
        source_root=root,
        source_index=_index(root),
        source_path="nested/course/main.tex",
    )

    assert [item.path for item in inputs] == [
        "course-style.bst",
        "lecture-notes.cls",
        "nested/course/main.tex",
        "references.bib",
    ]


def _index(root: Path) -> CourseSourceIndex:
    files = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        payload = path.read_bytes()
        suffix = path.suffix.lower()
        files.append(
            IndexedSourceFile(
                path=path.relative_to(root).as_posix(),
                kind=SOURCE_SUFFIXES[suffix],
                size_bytes=len(payload),
                sha256=hashlib.sha256(payload).hexdigest(),
                modified_ns=path.stat().st_mtime_ns,
            )
        )
    return CourseSourceIndex(course_id="demo-course", files=files)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
