from __future__ import annotations

from pathlib import Path

from lecturepilot.bounded_processing import BoundedProcessingError
from lecturepilot.canvas_models import CanvasBlock, CanvasSection
from lecturepilot.latex_canvas_text import slug
from lecturepilot.pdf_extract import pdf_page_count, read_pdf_page_range
from lecturepilot.pdf_slide_assets import PdfSlideAssetError, render_pdf_slide_blocks
from lecturepilot.source_bundle_media import media_caption
from lecturepilot.source_bundle_text import MAX_TEXT_CHARS_PER_FILE, pdf_text_blocks


PDF_PAGES_PER_SECTION = 12
MAX_PDF_SECTIONS = 8


class PdfSourceError(RuntimeError):
    pass


def pdf_sections(
    *,
    path: Path,
    source_ref: str,
    source_root: Path,
    derived_root: Path,
    course_id: str,
    lecture_id: str,
) -> list[CanvasSection]:
    page_count = _page_count(path)
    ranges = page_ranges(page_count)
    base_id = slug(source_ref)
    try:
        slides = render_pdf_slide_blocks(
            pdf_path=path,
            source_root=source_root,
            output_root=derived_root,
            course_id=course_id,
            lecture_id=lecture_id,
            source_ref=source_ref,
        )
    except PdfSlideAssetError as exc:
        raise PdfSourceError(str(exc)) from exc
    title = path.stem.replace("-", " ").replace("_", " ").title()
    sections = []
    for index, (start, end) in enumerate(ranges, start=1):
        section_id = base_id if len(ranges) == 1 else f"{base_id}-pages-{start + 1}-{end}"
        blocks = pdf_text_blocks(section_id, _page_text(path, start, end))
        if index == 1:
            blocks.append(
                CanvasBlock(
                    id=f"{section_id}-asset-1",
                    type="asset",
                    asset_path=source_ref,
                    asset_url=f"/course-assets/{course_id}/{lecture_id}/{source_ref}",
                    caption=media_caption(source_root, source_ref),
                )
            )
        blocks.extend(slide for slide in slides if start <= slide_number(slide) - 1 < end)
        if any(block.text or block.items for block in blocks):
            sections.append(
                CanvasSection(
                    id=section_id,
                    title=(title if len(ranges) == 1 else f"{title} · pages {start + 1}–{end}")[
                        :200
                    ],
                    source_ref=f"{source_ref} pages {start + 1}–{end}",
                    blocks=blocks,
                )
            )
    return sections


def page_ranges(page_count: int) -> list[tuple[int, int]]:
    if page_count <= 0:
        return []
    section_count = min(
        MAX_PDF_SECTIONS,
        max(1, (page_count + PDF_PAGES_PER_SECTION - 1) // PDF_PAGES_PER_SECTION),
    )
    boundaries = [round(index * page_count / section_count) for index in range(section_count + 1)]
    return [
        (boundaries[index], boundaries[index + 1])
        for index in range(section_count)
        if boundaries[index] < boundaries[index + 1]
    ]


def slide_number(block: CanvasBlock) -> int:
    name = (block.asset_path or "").rsplit("/", 1)[-1]
    if name.startswith("slide-") and name.endswith(".png"):
        value = name.removeprefix("slide-").removesuffix(".png")
        if value.isdigit():
            return int(value)
    return 0


def _page_text(path: Path, start_page: int, end_page: int) -> str:
    try:
        return read_pdf_page_range(
            str(path),
            start_page=start_page,
            end_page=end_page,
            max_chars=MAX_TEXT_CHARS_PER_FILE,
        )
    except (BoundedProcessingError, ImportError) as exc:
        raise PdfSourceError("PDF text extraction failed safely.") from exc


def _page_count(path: Path) -> int:
    try:
        return pdf_page_count(str(path))
    except (BoundedProcessingError, ImportError) as exc:
        raise PdfSourceError("PDF page inspection failed safely.") from exc
