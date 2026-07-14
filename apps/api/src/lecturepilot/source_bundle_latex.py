from __future__ import annotations

from pathlib import Path

from lecturepilot.canvas_models import CanvasSection
from lecturepilot.latex_canvas_text import slug


def source_kind(source_refs: list[str]) -> str:
    only_latex = source_refs and all(Path(path).suffix.lower() == ".tex" for path in source_refs)
    return "latex" if only_latex else "markdown"


def scoped_latex_sections(sections: list[CanvasSection], path: str) -> list[CanvasSection]:
    prefix = slug(Path(path).stem)
    return [
        section.model_copy(
            update={
                "id": f"{prefix}-{section.id}",
                "source_ref": f"{path} {section.source_ref or ''}".strip(),
                "blocks": [
                    block.model_copy(update={"id": f"{prefix}-{block.id}"})
                    for block in section.blocks
                ],
            }
        )
        for section in sections
    ]
