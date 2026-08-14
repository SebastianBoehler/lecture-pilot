from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from lecturepilot.canvas_models import CanvasBlock, CanvasSection
from lecturepilot.latex_canvas_text import slug
from lecturepilot.pdf_slide_assets import PdfSlideAssetError, render_pdf_slide_blocks
from lecturepilot.source_bundle import SourceBundleFile
from lecturepilot.source_bundle_pdf import slide_number
from lecturepilot.source_normalization_models import NormalizedBlock, NormalizedDocument
from lecturepilot.source_normalization_store import (
    SourceNormalizationError,
    load_normalized_document,
)


MAX_TABLE_ROWS = 100
MAX_TABLE_COLUMNS = 30
MAX_CELL_CHARS = 200


class NormalizedCanvasError(RuntimeError):
    pass


def normalized_sections(
    *,
    file: SourceBundleFile,
    normalized_root: Path,
    course_id: str,
    lecture_id: str,
) -> tuple[list[CanvasSection], list[str]]:
    if not file.sha256:
        raise NormalizedCanvasError(f"Normalized revision is missing for {file.path}.")
    try:
        document = load_normalized_document(normalized_root, file.sha256)
    except SourceNormalizationError as exc:
        raise NormalizedCanvasError(f"Normalized source is unavailable for {file.path}.") from exc
    if document.source_path != file.path:
        raise NormalizedCanvasError(f"Normalized source path does not match {file.path}.")
    if file.kind == "presentation":
        sections = _presentation_sections(
            document,
            revision_root=normalized_root / file.sha256,
            normalized_root=normalized_root,
            course_id=course_id,
            lecture_id=lecture_id,
        )
    elif file.kind == "spreadsheet":
        sections = _spreadsheet_sections(document)
    else:
        sections = _document_sections(document)
    return sections, document.warnings


def _presentation_sections(
    document: NormalizedDocument,
    *,
    revision_root: Path,
    normalized_root: Path,
    course_id: str,
    lecture_id: str,
) -> list[CanvasSection]:
    grouped: dict[int, list[NormalizedBlock]] = defaultdict(list)
    for block in document.blocks:
        grouped[block.locator.slide or 1].append(block)
    slides = _rendered_slides(
        revision_root / "rendered.pdf",
        normalized_root=normalized_root,
        course_id=course_id,
        lecture_id=lecture_id,
        source_ref=document.source_path,
    )
    for slide in slides:
        grouped.setdefault(slide_number(slide), [])
    sections = []
    for number, blocks in sorted(grouped.items()):
        canvas_blocks = [
            converted
            for index, block in enumerate(blocks, start=1)
            if (converted := _canvas_block(document.source_path, block, index=index))
        ]
        canvas_blocks.extend(slide for slide in slides if slide_number(slide) == number)
        if not canvas_blocks:
            continue
        sections.append(
            CanvasSection(
                id=f"{slug(document.source_path)}-slide-{number}",
                title=_block_title(blocks) or f"Slide {number}",
                source_ref=f"{document.source_path} slide {number}",
                blocks=canvas_blocks,
            )
        )
    return sections


def _rendered_slides(
    path: Path,
    *,
    normalized_root: Path,
    course_id: str,
    lecture_id: str,
    source_ref: str,
) -> list[CanvasBlock]:
    if not path.is_file():
        return []
    try:
        return render_pdf_slide_blocks(
            pdf_path=path,
            source_root=normalized_root,
            output_root=normalized_root,
            course_id=course_id,
            lecture_id=lecture_id,
            source_ref=source_ref,
        )
    except PdfSlideAssetError as exc:
        raise NormalizedCanvasError(f"Rendered slide preview failed for {source_ref}.") from exc


def _spreadsheet_sections(document: NormalizedDocument) -> list[CanvasSection]:
    sections = []
    for index, block in enumerate(document.blocks, start=1):
        if block.kind != "table" or not block.cells:
            continue
        sheet = block.locator.sheet or f"Sheet {index}"
        cell_range = block.locator.cell_range or "used cells"
        sections.append(
            CanvasSection(
                id=f"{slug(document.source_path)}-sheet-{slug(sheet)}",
                title=sheet[:200],
                source_ref=f"{document.source_path} sheet {sheet} {cell_range}",
                blocks=[
                    CanvasBlock(
                        id=f"{slug(document.source_path)}-table-{index}",
                        type="table",
                        text=_markdown_table(block),
                    )
                ],
            )
        )
    return sections


def _document_sections(document: NormalizedDocument) -> list[CanvasSection]:
    blocks = [
        converted
        for index, block in enumerate(document.blocks, start=1)
        if (converted := _canvas_block(document.source_path, block, index=index))
    ]
    if not blocks:
        return []
    return [
        CanvasSection(
            id=slug(document.source_path),
            title=_block_title(document.blocks) or _filename_title(document.source_path),
            source_ref=document.source_path,
            blocks=blocks,
        )
    ]


def _canvas_block(source_ref: str, block: NormalizedBlock, *, index: int) -> CanvasBlock | None:
    text = block.text
    if block.kind == "link" and block.url:
        text = f"[{text or str(block.url)}]({block.url})"
    if not text:
        return None
    block_type = "math" if block.kind == "formula" else "paragraph"
    if block.kind == "code":
        text = f"```text\n{text}\n```"
    return CanvasBlock(
        id=f"{slug(source_ref)}-normalized-{index}",
        type=block_type,
        text=text,
    )


def _markdown_table(block: NormalizedBlock) -> str:
    rows = min(MAX_TABLE_ROWS, max(cell.row for cell in block.cells))
    columns = min(MAX_TABLE_COLUMNS, max(cell.column for cell in block.cells))
    values = {(cell.row, cell.column): _cell_text(cell.value, cell.formula) for cell in block.cells}
    matrix = [
        [values.get((row, column), "") for column in range(1, columns + 1)]
        for row in range(1, rows + 1)
    ]
    header = matrix[0]
    return "\n".join(
        [
            _markdown_row(header),
            _markdown_row(["---"] * columns),
            *[_markdown_row(row) for row in matrix[1:]],
        ]
    )


def _cell_text(value: object, formula: str | None) -> str:
    if value is None and formula:
        return f"`{formula[:MAX_CELL_CHARS]}`"
    return str(value if value is not None else "")[:MAX_CELL_CHARS]


def _markdown_row(values: list[str]) -> str:
    escaped = [value.replace("|", "\\|").replace("\n", " ") for value in values]
    return f"| {' | '.join(escaped)} |"


def _block_title(blocks: list[NormalizedBlock]) -> str | None:
    return next(
        (block.text[:200] for block in blocks if block.kind == "heading" and block.text), None
    )


def _filename_title(source_path: str) -> str:
    return Path(source_path).stem.replace("-", " ").replace("_", " ").title()[:200]
