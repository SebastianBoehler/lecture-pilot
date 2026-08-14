import json
from pathlib import Path

from lecturepilot.source_bundle import SourceBundleFile
from lecturepilot.source_bundle_canvas import import_source_bundle_canvas
from test_source_bundle_canvas import _write, _write_pdf


def test_normalized_powerpoint_adds_native_text_links_and_rendered_slides(
    tmp_path: Path,
) -> None:
    root = tmp_path / "bundle"
    derived = tmp_path / "normalized"
    source_sha256 = "a" * 64
    _write(root / "slides" / "lecture.pptx", "OOXML placeholder")
    _write_normalized_manifest(
        derived,
        source_sha256,
        source_path="slides/lecture.pptx",
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        blocks=[
            _normalized_block("heading", "Bayesian evidence", slide=1),
            _normalized_block("paragraph", "Update the prior from evidence.", slide=1),
            {
                **_normalized_block("link", "External dataset", slide=1),
                "url": "https://example.edu/data",
            },
            _normalized_block("heading", "Decision risk", slide=2),
            _normalized_block("paragraph", "Compare posterior action costs.", slide=2),
        ],
    )
    _write_pdf(
        derived / source_sha256 / "rendered.pdf",
        "Rendered Bayesian evidence slide.",
        "Rendered decision risk slide.",
    )

    document = import_source_bundle_canvas(
        source_root=root,
        course_id="demo-course",
        lecture_id="lecture-01",
        workspace_path="planner/source.json",
        files=[
            SourceBundleFile(
                path="slides/lecture.pptx",
                kind="presentation",
                size_bytes=10,
                sha256=source_sha256,
            )
        ],
        derived_root=derived,
    )

    assert [section.source_ref for section in document.sections] == [
        "slides/lecture.pptx slide 1",
        "slides/lecture.pptx slide 2",
    ]
    all_text = "\n".join(
        block.text or "" for section in document.sections for block in section.blocks
    )
    assert "[External dataset](https://example.edu/data)" in all_text
    slide_blocks = [
        block
        for section in document.sections
        for block in section.blocks
        if block.asset_path and block.asset_path.startswith("generated-slides/")
    ]
    assert [block.caption for block in slide_blocks] == [
        "Original slide 1 from slides/lecture.pptx",
        "Original slide 2 from slides/lecture.pptx",
    ]


def test_normalized_spreadsheet_becomes_source_located_table_artifact(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    derived = tmp_path / "normalized"
    source_sha256 = "b" * 64
    _write(root / "data" / "results.xlsx", "OOXML placeholder")
    _write_normalized_manifest(
        derived,
        source_sha256,
        source_path="data/results.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        blocks=[
            {
                "kind": "table",
                "cells": [
                    {"row": 1, "column": 1, "value": "Method"},
                    {"row": 1, "column": 2, "value": "Score"},
                    {"row": 2, "column": 1, "value": "OLS"},
                    {"row": 2, "column": 2, "value": 0.9},
                    {"row": 3, "column": 2, "formula": "=SUM(B2)"},
                ],
                "locator": {"sheet": "Regression", "cell_range": "A1:B3"},
                "extraction": "native",
            }
        ],
    )

    document = import_source_bundle_canvas(
        source_root=root,
        course_id="demo-course",
        lecture_id="lecture-01",
        workspace_path="planner/source.json",
        files=[
            SourceBundleFile(
                path="data/results.xlsx",
                kind="spreadsheet",
                size_bytes=10,
                sha256=source_sha256,
            )
        ],
        derived_root=derived,
    )

    section = document.sections[0]
    assert section.source_ref == "data/results.xlsx sheet Regression A1:B3"
    assert section.blocks[0].type == "table"
    assert section.blocks[0].text == (
        "| Method | Score |\n| --- | --- |\n| OLS | 0.9 |\n|  | `=SUM(B2)` |"
    )


def _write_normalized_manifest(
    root: Path,
    source_sha256: str,
    *,
    source_path: str,
    media_type: str,
    blocks: list[dict],
) -> None:
    revision = root / source_sha256
    revision.mkdir(parents=True)
    (revision / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_path": source_path,
                "source_sha256": source_sha256,
                "media_type": media_type,
                "blocks": blocks,
                "warnings": [],
            }
        ),
        encoding="utf-8",
    )


def _normalized_block(kind: str, text: str, *, slide: int) -> dict:
    return {
        "kind": kind,
        "text": text,
        "locator": {"slide": slide},
        "extraction": "native",
    }
