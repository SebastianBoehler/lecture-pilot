from __future__ import annotations

import csv
from itertools import islice
from pathlib import Path

from lecturepilot.canvas_models import CanvasBlock, CanvasSection
from lecturepilot.latex_canvas_text import slug


MAX_ROWS = 100
MAX_COLUMNS = 30
MAX_CELL_CHARS = 200


class SourceTableError(RuntimeError):
    pass


def csv_section(path: Path, source_ref: str) -> CanvasSection | None:
    try:
        with path.open(encoding="utf-8-sig", errors="replace", newline="") as handle:
            rows = [
                [_cell(value) for value in row[:MAX_COLUMNS]]
                for row in islice(csv.reader(handle), MAX_ROWS)
            ]
    except (OSError, csv.Error) as exc:
        raise SourceTableError(f"Could not read table source {path.name}.") from exc
    columns = max((len(row) for row in rows), default=0)
    if not rows or not columns:
        return None
    matrix = [row + [""] * (columns - len(row)) for row in rows]
    markdown = "\n".join(
        [
            _markdown_row(matrix[0]),
            _markdown_row(["---"] * columns),
            *[_markdown_row(row) for row in matrix[1:]],
        ]
    )
    return CanvasSection(
        id=slug(source_ref),
        title=path.stem.replace("-", " ").replace("_", " ").title()[:200],
        source_ref=source_ref,
        blocks=[
            CanvasBlock(
                id=f"{slug(source_ref)}-table-1",
                type="table",
                text=markdown,
            )
        ],
    )


def _cell(value: str) -> str:
    return value.strip().replace("\x00", "")[:MAX_CELL_CHARS]


def _markdown_row(values: list[str]) -> str:
    escaped = [value.replace("|", "\\|").replace("\n", " ") for value in values]
    return f"| {' | '.join(escaped)} |"
