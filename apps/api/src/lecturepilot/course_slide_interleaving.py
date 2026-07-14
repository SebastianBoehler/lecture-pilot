from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import PurePosixPath

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection


MAX_ORIGINAL_SLIDES_PER_SECTION = 2


@dataclass(frozen=True)
class _SourceSlide:
    block: CanvasBlock
    source_ref: str
    page_number: int


def interleave_original_slides(
    document: CanvasDocument, source_document: CanvasDocument
) -> CanvasDocument:
    slides_by_source = _source_slides(source_document)
    if not slides_by_source or not document.sections:
        return document
    unique_basenames = _unique_source_basenames(slides_by_source)
    companion_positions = _companion_section_positions(
        document.sections,
        slides_by_source,
        unique_basenames,
    )
    used = {
        block.asset_path
        for section in document.sections
        for block in section.blocks
        if _is_original_slide(block) and block.asset_path
    }
    sections = []
    for index, section in enumerate(document.sections):
        capacity = MAX_ORIGINAL_SLIDES_PER_SECTION - _original_slide_count(section)
        selected = _select_slides(
            section=section,
            section_index=index,
            capacity=max(0, capacity),
            slides_by_source=slides_by_source,
            unique_basenames=unique_basenames,
            companion_positions=companion_positions,
            used=used,
        )
        sections.append(_with_slides(section, selected))
    return document.model_copy(update={"sections": sections})


def _with_slides(section: CanvasSection, slides: list[CanvasBlock]) -> CanvasSection:
    if not slides:
        return section
    blocks = list(section.blocks)
    if _original_slide_count(section) == 0:
        blocks.insert(0, slides.pop(0))
    for slide in slides:
        blocks.insert(_after_teaching_blocks(blocks, count=2), slide)
    return section.model_copy(update={"blocks": blocks})


def _select_slides(
    *,
    section: CanvasSection,
    section_index: int,
    capacity: int,
    slides_by_source: dict[str, list[_SourceSlide]],
    unique_basenames: set[str],
    companion_positions: dict[str, list[int]],
    used: set[str],
) -> list[CanvasBlock]:
    if capacity == 0:
        return []
    selected: list[_SourceSlide] = []
    source_ref = section.source_ref or ""
    for source_slides in slides_by_source.values():
        ranges = _pdf_page_ranges(source_ref, source_slides[0].source_ref, unique_basenames)
        if ranges:
            matches = [
                slide
                for slide in source_slides
                if _page_in_ranges(slide.page_number, ranges) and _slide_identity(slide) not in used
            ]
            selected.extend(_spread(matches, capacity - len(selected)))
        if len(selected) >= capacity:
            break
    for source_key, positions in companion_positions.items():
        if len(selected) >= capacity or section_index not in positions:
            continue
        source_slides = slides_by_source[source_key]
        position = positions.index(section_index)
        excluded = used | {_slide_identity(slide) for slide in selected}
        selected.extend(
            _companion_bucket(
                source_slides,
                position,
                len(positions),
                capacity - len(selected),
                excluded,
            )
        )
    blocks: list[CanvasBlock] = []
    for slide in selected:
        identity = slide.block.asset_path or slide.block.id
        if identity in used:
            continue
        used.add(identity)
        blocks.append(slide.block)
        if len(blocks) == capacity:
            break
    return blocks


def _source_slides(document: CanvasDocument) -> dict[str, list[_SourceSlide]]:
    grouped: dict[str, list[_SourceSlide]] = defaultdict(list)
    seen: set[str] = set()
    for block in (
        block
        for section in document.sections
        for block in section.blocks
        if _is_original_slide(block)
    ):
        parsed = _slide_metadata(block)
        if parsed and _slide_identity(parsed) not in seen:
            seen.add(_slide_identity(parsed))
            grouped[_source_key(parsed.source_ref)].append(parsed)
    return {
        source_key: sorted(source_slides, key=lambda slide: slide.page_number)
        for source_key, source_slides in sorted(grouped.items())
    }


def _companion_section_positions(
    sections: list[CanvasSection],
    slides_by_source: dict[str, list[_SourceSlide]],
    unique_basenames: set[str],
) -> dict[str, list[int]]:
    positions: dict[str, list[int]] = {}
    for source_key, slides in slides_by_source.items():
        source_ref = slides[0].source_ref
        companion_ref = f"{source_ref[:-4]}.tex"
        matches = [
            index
            for index, section in enumerate(sections)
            if _mentions_source(section.source_ref or "", companion_ref, unique_basenames)
        ]
        if matches:
            positions[source_key] = matches
    return positions


def _companion_bucket(
    slides: list[_SourceSlide],
    position: int,
    section_count: int,
    limit: int,
    excluded: set[str],
) -> list[_SourceSlide]:
    if not slides or limit <= 0:
        return []
    if len(slides) < section_count:
        if len(slides) == 1:
            slide = slides[0]
            return [slide] if position == 0 and _slide_identity(slide) not in excluded else []
        section_positions = {
            round(slide_index * (section_count - 1) / (len(slides) - 1)): slide
            for slide_index, slide in enumerate(slides)
        }
        slide = section_positions.get(position)
        return [slide] if slide and _slide_identity(slide) not in excluded else []
    start = position * len(slides) // section_count
    end = (position + 1) * len(slides) // section_count
    available = [slide for slide in slides[start:end] if _slide_identity(slide) not in excluded]
    return _spread(available, limit)


def _spread(slides: list[_SourceSlide], limit: int) -> list[_SourceSlide]:
    if limit <= 0 or not slides:
        return []
    if len(slides) <= limit:
        return slides
    if limit == 1:
        return [slides[0]]
    return [slides[round(index * (len(slides) - 1) / (limit - 1))] for index in range(limit)]


def _pdf_page_ranges(
    section_ref: str,
    pdf_source_ref: str,
    unique_basenames: set[str],
) -> list[tuple[int, int]]:
    aliases = _source_aliases(pdf_source_ref, unique_basenames)
    for alias in aliases:
        match = re.search(
            rf"(?<![\w.-]){re.escape(alias)}\s+pages?\s+([0-9,\s\-\u2013\u2014]+)",
            section_ref,
            flags=re.I,
        )
        if not match:
            continue
        ranges = []
        for number_match in re.finditer(r"(\d+)(?:\s*[-\u2013\u2014]\s*(\d+))?", match.group(1)):
            start = int(number_match.group(1))
            end = int(number_match.group(2) or start)
            ranges.append((min(start, end), max(start, end)))
        return ranges
    return []


def _page_in_ranges(page_number: int, ranges: list[tuple[int, int]]) -> bool:
    return any(start <= page_number <= end for start, end in ranges)


def _mentions_source(section_ref: str, source_ref: str, unique_basenames: set[str]) -> bool:
    return any(
        re.search(rf"(?<![\w.-]){re.escape(alias)}(?![\w.-])", section_ref, flags=re.I)
        for alias in _source_aliases(source_ref, unique_basenames)
    )


def _source_aliases(source_ref: str, unique_basenames: set[str]) -> list[str]:
    aliases = [source_ref]
    basename = PurePosixPath(source_ref).name
    pdf_basename = f"{PurePosixPath(source_ref).stem}.pdf".casefold()
    if pdf_basename in unique_basenames and basename.casefold() != source_ref.casefold():
        aliases.append(basename)
    return aliases


def _unique_source_basenames(slides_by_source: dict[str, list[_SourceSlide]]) -> set[str]:
    counts: dict[str, int] = defaultdict(int)
    for slides in slides_by_source.values():
        counts[PurePosixPath(slides[0].source_ref).name.casefold()] += 1
    return {basename for basename, count in counts.items() if count == 1}


def _slide_metadata(block: CanvasBlock) -> _SourceSlide | None:
    match = re.fullmatch(r"(?:Original|Compiled) slide (\d+) from (.+)", block.caption or "")
    if not match:
        return None
    return _SourceSlide(block=block, source_ref=match.group(2), page_number=int(match.group(1)))


def _slide_identity(slide: _SourceSlide) -> str:
    return slide.block.asset_path or slide.block.id


def _source_key(source_ref: str) -> str:
    return PurePosixPath(source_ref).as_posix().casefold()


def _is_original_slide(block: CanvasBlock) -> bool:
    return bool(
        block.type == "asset"
        and block.asset_path
        and block.asset_path.startswith("generated-slides/")
        and block.caption
        and block.caption.startswith(("Original slide ", "Compiled slide "))
    )


def _original_slide_count(section: CanvasSection) -> int:
    return sum(_is_original_slide(block) for block in section.blocks)


def _after_teaching_blocks(blocks: list[CanvasBlock], *, count: int) -> int:
    teaching_blocks = 0
    for index, block in enumerate(blocks):
        if _is_original_slide(block):
            continue
        teaching_blocks += 1
        if teaching_blocks == count:
            return index + 1
    return len(blocks)
