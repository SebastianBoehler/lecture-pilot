from pathlib import Path, PurePosixPath

from lecturepilot_latex_compiler.source_compatibility import _planned_case_aliases


def test_plans_exact_case_alias_for_graphicspath_asset(tmp_path: Path) -> None:
    _write(
        tmp_path / "slides.tex",
        r"""
        \graphicspath{{images/deepnets/}}
        \includegraphics{initialization_xavier}
        """,
    )
    (tmp_path / "images/deepnets").mkdir(parents=True)
    (tmp_path / "images/deepnets/initialization_Xavier.PNG").write_bytes(b"image")

    aliases = _planned_case_aliases(tmp_path)

    assert aliases == [
        (
            PurePosixPath("images/deepnets/initialization_xavier.png"),
            PurePosixPath("images/deepnets/initialization_Xavier.PNG"),
        )
    ]


def test_keeps_distinct_case_spellings_used_by_different_sources(
    tmp_path: Path,
) -> None:
    _write(tmp_path / "one.tex", r"\includegraphics{images/diagram}")
    _write(tmp_path / "two.tex", r"\includegraphics{images/DIAGRAM}")
    (tmp_path / "images").mkdir()
    (tmp_path / "images/Diagram.png").write_bytes(b"image")

    aliases = _planned_case_aliases(tmp_path)

    assert {requested for requested, _ in aliases} == {
        PurePosixPath("images/diagram.png"),
        PurePosixPath("images/DIAGRAM.png"),
    }


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
