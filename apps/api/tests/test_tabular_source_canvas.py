from pathlib import Path

from lecturepilot.source_bundle_canvas import import_source_bundle_canvas
from test_source_bundle_canvas import _write


def test_csv_and_json_sources_remain_inert_canvas_evidence(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    _write(root / "data" / "results.csv", "Method,Score\nOLS,0.9\nRidge,0.92\n")
    _write(root / "config" / "experiment.json", '{"metric": "accuracy"}')

    document = import_source_bundle_canvas(
        source_root=root,
        course_id="demo-course",
        lecture_id="lecture-01",
        workspace_path="planner/source.json",
    )

    blocks = [block for section in document.sections for block in section.blocks]
    assert next(block.text for block in blocks if block.type == "table") == (
        "| Method | Score |\n| --- | --- |\n| OLS | 0.9 |\n| Ridge | 0.92 |"
    )
    assert any(block.text == '```json\n{"metric": "accuracy"}\n```' for block in blocks)
