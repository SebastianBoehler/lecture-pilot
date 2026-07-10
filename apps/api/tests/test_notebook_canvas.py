from __future__ import annotations

import json
from pathlib import Path

import pytest

from lecturepilot.canvas_markdown import read_document_source, write_document_source
from lecturepilot.canvas_text_normalizer import clean_canvas_text
from lecturepilot.course_canvas_planner import _read_block as read_planned_block
from lecturepilot.course_canvas_prompt import planner_messages
from lecturepilot.course_canvas_section_planner import _read_block as read_section_planned_block
from lecturepilot.source_bundle_canvas import (
    SourceBundleCanvasError,
    import_source_bundle_canvas,
)


def test_notebook_imports_markdown_and_code_without_outputs(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    notebook = root / "Lecture01" / "gradient-descent.ipynb"
    _write_notebook(
        notebook,
        [
            {
                "cell_type": "markdown",
                "source": ["# Gradient Descent\n", "We update parameters from the loss gradient."],
            },
            {
                "cell_type": "code",
                "source": [
                    "def step(theta, gradient, rate):\n",
                    "    return theta - rate * gradient\n",
                ],
                "outputs": [{"output_type": "stream", "text": ["PRIVATE-STUDENT-OUTPUT"]}],
                "execution_count": 7,
            },
            {"cell_type": "markdown", "source": "The learning rate controls the update size."},
            {
                "cell_type": "markdown",
                "source": (
                    "![Remote diagram](https://tracker.invalid/pixel)\n"
                    "A referenced diagram supports the explanation."
                ),
            },
        ],
    )

    document = import_source_bundle_canvas(
        source_root=root,
        course_id="ml-course",
        lecture_id="lecture-01",
        workspace_path="planner/source.json",
    )

    assert document.source_ref == "Lecture01/gradient-descent.ipynb"
    assert [section.title for section in document.sections] == ["Gradient Descent"]
    blocks = document.sections[0].blocks
    assert [block.type for block in blocks] == [
        "paragraph",
        "paragraph",
        "paragraph",
        "paragraph",
    ]
    assert blocks[0].text == "# Gradient Descent\nWe update parameters from the loss gradient."
    assert blocks[1].text == (
        "```python\ndef step(theta, gradient, rate):\n    return theta - rate * gradient\n```"
    )
    assert blocks[2].text == "The learning rate controls the update size."
    assert blocks[3].text == "Remote diagram\nA referenced diagram supports the explanation."
    assert "tracker.invalid" not in document.model_dump_json()
    assert "PRIVATE-STUDENT-OUTPUT" not in document.model_dump_json()

    canvas_dir = tmp_path / "canvas"
    write_document_source(document, canvas_dir)
    reloaded = read_document_source(canvas_dir)
    assert reloaded.sections[0].blocks[1].text == blocks[1].text


def test_python_source_imports_as_a_fenced_code_snippet(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    source = root / "Lecture01" / "linear_model.py"
    source.parent.mkdir(parents=True)
    source.write_text("def predict(x, weight):\n    return x * weight\n", encoding="utf-8")

    document = import_source_bundle_canvas(
        source_root=root,
        course_id="ml-course",
        lecture_id="lecture-01",
        workspace_path="planner/source.json",
    )

    assert document.source_ref == "Lecture01/linear_model.py"
    section = document.sections[0]
    assert section.title == "Linear Model"
    assert section.blocks[0].text == (
        "```python\ndef predict(x, weight):\n    return x * weight\n```"
    )


def test_notebook_code_keeps_indentation_across_planner_boundaries(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    source = root / "Lecture01" / "linear_model.py"
    source.parent.mkdir(parents=True)
    source.write_text("def predict(x):\n    return x * 2\n", encoding="utf-8")
    document = import_source_bundle_canvas(
        source_root=root,
        course_id="ml-course",
        lecture_id="lecture-01",
        workspace_path="planner/source.json",
    )
    code = document.sections[0].blocks[0].text or ""

    assert code in planner_messages(document)[1]["content"]
    assert "preserve it" in planner_messages(document)[0]["content"]
    assert clean_canvas_text(code) == code
    assert read_planned_block({"text": code}, "code-1", "paragraph", {}).text == code
    assert read_section_planned_block({"text": code}, "code-1", "paragraph", {}).text == code


def test_malformed_notebook_returns_a_controlled_error(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    notebook = root / "Lecture01" / "broken.ipynb"
    notebook.parent.mkdir(parents=True)
    notebook.write_text("{not-json", encoding="utf-8")

    with pytest.raises(
        SourceBundleCanvasError,
        match=r"Could not read notebook broken\.ipynb\.",
    ):
        import_source_bundle_canvas(
            source_root=root,
            course_id="ml-course",
            lecture_id="lecture-01",
            workspace_path="planner/source.json",
        )


def _write_notebook(path: Path, cells: list[dict]) -> None:
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "cells": cells,
                "metadata": {
                    "kernelspec": {"display_name": "Python 3", "language": "python"},
                    "language_info": {"name": "python"},
                },
                "nbformat": 4,
                "nbformat_minor": 5,
            }
        ),
        encoding="utf-8",
    )
