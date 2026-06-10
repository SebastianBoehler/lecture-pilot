from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from lecturepilot.canvas_models import CanvasBlock, CanvasSection
from lecturepilot.latex_canvas_text import paragraphs_from_latex, read_assets, read_items, read_math_blocks, slug


class LatexFrameLike(Protocol):
    index: int
    title: str
    body: str
    slug: str


@dataclass(frozen=True)
class StudyGroup:
    id: str
    title: str
    frames: tuple[LatexFrameLike, ...]


def read_study_sections(
    frames: list[LatexFrameLike],
    material_root: Path,
    course_id: str,
    lecture_id: str,
) -> list[CanvasSection]:
    sections: list[CanvasSection] = []
    for group in _study_groups(frames):
        blocks = _study_blocks(group, material_root, course_id, lecture_id)
        if blocks:
            sections.append(
                CanvasSection(
                    id=group.id,
                    title=group.title,
                    source_ref=_source_ref(group.frames),
                    blocks=blocks,
                )
            )
    return sections


def _study_groups(frames: list[LatexFrameLike]) -> list[StudyGroup]:
    if len(frames) < 8:
        return []
    chunk_size = max(2, math.ceil(len(frames) / 12))
    chunks = [frames[index : index + chunk_size] for index in range(0, len(frames), chunk_size)]
    if len(chunks) > 1 and len(chunks[-1]) == 1:
        chunks[-2].extend(chunks.pop())

    seen: dict[str, int] = {}
    groups = []
    for chunk in chunks:
        title = _group_title(chunk)
        group_id = _unique_id(title, seen)
        groups.append(StudyGroup(id=group_id, title=title, frames=tuple(chunk)))
    return groups


def _study_blocks(
    group: StudyGroup,
    material_root: Path,
    course_id: str,
    lecture_id: str,
) -> list[CanvasBlock]:
    body = "\n".join(frame.body for frame in group.frames)
    blocks: list[CanvasBlock] = []

    for index, paragraph in enumerate(paragraphs_from_latex(body)[:2], start=1):
        blocks.append(CanvasBlock(id=f"{group.id}-p-{index}", type="paragraph", text=paragraph))

    if items := read_items(body):
        blocks.append(CanvasBlock(id=f"{group.id}-list", type="list", items=items[:8]))

    for index, asset in enumerate(read_assets(body, material_root=material_root)[:2], start=1):
        blocks.append(
            CanvasBlock(
                id=f"{group.id}-asset-{index}",
                type="asset",
                asset_path=asset,
                asset_url=f"/course-assets/{course_id}/{lecture_id}/{asset}",
                caption=asset,
            )
        )

    formulas = read_math_blocks(body)
    for index, formula in enumerate(formulas[:3], start=1):
        blocks.append(CanvasBlock(id=f"{group.id}-math-{index}", type="math", text=formula))
    if len(formulas) > 3:
        blocks.append(
            CanvasBlock(
                id=f"{group.id}-derivation-note",
                type="callout",
                text="Additional derivation steps stay linked in the source frames; this canvas keeps the key formulas visible.",
            )
        )
    return blocks


def _group_title(frames: list[LatexFrameLike]) -> str:
    titles = [_clean_title(frame.title) for frame in frames if frame.title]
    if not titles:
        return "Lecture topic"
    first = titles[0]
    last = next((title for title in reversed(titles) if title != first), "")
    if last and len(f"{first}: {last}") <= 90:
        return f"{first}: {last}"
    return first


def _clean_title(title: str) -> str:
    return re.sub(r"\s+", " ", title.replace("--", "-")).strip()


def _unique_id(title: str, seen: dict[str, int]) -> str:
    base = slug(title)
    seen[base] = seen.get(base, 0) + 1
    return base if seen[base] == 1 else f"{base}-{seen[base]}"


def _source_ref(frames: tuple[LatexFrameLike, ...]) -> str:
    return "frames " + ", ".join(str(frame.index) for frame in frames)
