from pathlib import Path

from lecturepilot.latex_canvas_importer import import_latex_canvas


def test_latex_import_resolves_graphicspath_assets_from_nested_source(tmp_path: Path) -> None:
    source_dir = tmp_path / "course" / "lectures" / "week-02"
    image_dir = source_dir / "images" / "examples"
    image_dir.mkdir(parents=True)
    (image_dir / "pipeline.png").write_bytes(b"png")
    source_path = source_dir / "Lecture02.tex"
    source_path.write_text(
        r"""
\graphicspath{{figures/}{images/}}
\begin{frame}{Pipeline example}
The pipeline image shows the complete model training process.
\includegraphics{examples/pipeline}
\end{frame}
""",
        encoding="utf-8",
    )

    document = _import(source_path, source_dir)

    assert _asset_paths(document) == ["images/examples/pipeline.png"]


def test_latex_import_uses_first_existing_graphicspath_root(tmp_path: Path) -> None:
    material_root = tmp_path / "course"
    (material_root / "figures").mkdir(parents=True)
    (material_root / "images").mkdir()
    (material_root / "figures" / "shared.svg").write_text("<svg></svg>", encoding="utf-8")
    (material_root / "images" / "shared.png").write_bytes(b"png")
    source_path = material_root / "Lecture02.tex"
    source_path.write_text(
        r"""
\graphicspath{
  {figures/}
  {images/}
}
\begin{frame}{Shared figure}
This figure has enough explanatory text to become learning content.
\ig{shared}
\end{frame}
""",
        encoding="utf-8",
    )

    document = _import(source_path, material_root)

    assert _asset_paths(document) == ["figures/shared.svg"]


def test_latex_import_rejects_unsafe_graphicspath_traversal(tmp_path: Path) -> None:
    material_root = tmp_path / "course"
    material_root.mkdir()
    outside = tmp_path / "private"
    outside.mkdir()
    (outside / "secret.png").write_bytes(b"png")
    source_path = material_root / "Lecture02.tex"
    source_path.write_text(
        r"""
\graphicspath{{../private/}{images/}}
\begin{frame}{Unsafe figures}
This frame must not expose files outside the uploaded course material.
\includegraphics{secret}
\includegraphics{../private/secret.png}
\end{frame}
""",
        encoding="utf-8",
    )

    document = _import(source_path, material_root)

    assert _asset_paths(document) == []


def _import(source_path: Path, material_root: Path):
    return import_latex_canvas(
        source_path=source_path,
        material_root=material_root,
        course_id="ml-course",
        lecture_id="lecture-02",
        workspace_path="canvas/index.md",
    )


def _asset_paths(document) -> list[str]:
    return [
        block.asset_path
        for section in document.sections
        for block in section.blocks
        if block.type == "asset" and block.asset_path
    ]
