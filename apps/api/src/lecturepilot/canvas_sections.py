from __future__ import annotations

from lecturepilot.canvas_models import CanvasSection


def merge_sections(sections: list[CanvasSection]) -> list[CanvasSection]:
    result: list[CanvasSection] = []
    by_id: dict[str, int] = {}
    for section in sections:
        if section.id in by_id:
            result[by_id[section.id]] = section
            continue
        by_id[section.id] = len(result)
        result.append(section)
    return result
