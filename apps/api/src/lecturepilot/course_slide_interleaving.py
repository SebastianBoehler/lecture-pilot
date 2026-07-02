from __future__ import annotations

import re

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection


def interleave_original_slides(document: CanvasDocument, source_document: CanvasDocument) -> CanvasDocument:
    slides = _source_slides(source_document)
    if not slides or not document.sections:
        return document
    used: set[str] = set()
    sections = [
        _with_slide(section, _select_slide(section, slides, index, len(document.sections), used))
        for index, section in enumerate(document.sections)
    ]
    return document.model_copy(update={"sections": sections})


def _with_slide(section: CanvasSection, slide: CanvasBlock | None) -> CanvasSection:
    if slide is None or _starts_with_original_slide(section):
        return section
    return section.model_copy(update={"blocks": [slide, *section.blocks]})


def _select_slide(
    section: CanvasSection,
    slides: list[CanvasBlock],
    index: int,
    section_count: int,
    used: set[str],
) -> CanvasBlock | None:
    for page_number in _page_numbers(section.source_ref or ""):
        if 1 <= page_number <= len(slides):
            slide = slides[page_number - 1]
            if slide.id not in used:
                used.add(slide.id)
                return slide
    slide_index = round(index * (len(slides) - 1) / max(1, section_count - 1))
    for offset in range(len(slides)):
        slide = slides[(slide_index + offset) % len(slides)]
        if slide.id not in used:
            used.add(slide.id)
            return slide
    return None


def _source_slides(document: CanvasDocument) -> list[CanvasBlock]:
    slides = [
        block
        for section in document.sections
        for block in section.blocks
        if block.type == "asset"
        and block.asset_path
        and block.asset_path.startswith("generated-slides/")
        and block.caption
        and block.caption.startswith("Original slide ")
    ]
    return sorted(slides, key=lambda block: _slide_number(block.caption or "", block.asset_path or ""))


def _starts_with_original_slide(section: CanvasSection) -> bool:
    first = section.blocks[0] if section.blocks else None
    return bool(first and first.type == "asset" and first.asset_path and first.asset_path.startswith("generated-slides/"))


def _page_numbers(source_ref: str) -> list[int]:
    numbers: list[int] = []
    for match in re.finditer(r"(?:page|pages|frame|frames)\s+(\d+)(?:\s*-\s*(\d+))?", source_ref, flags=re.I):
        start = int(match.group(1))
        end = int(match.group(2) or start)
        numbers.extend(range(start, end + 1))
    return numbers


def _slide_number(caption: str, asset_path: str) -> int:
    match = re.search(r"Original slide (\d+)", caption) or re.search(r"slide-(\d+)", asset_path)
    return int(match.group(1)) if match else 0
