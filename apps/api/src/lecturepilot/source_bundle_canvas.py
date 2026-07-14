from __future__ import annotations

from pathlib import Path

from lecturepilot.bounded_processing import BoundedProcessingError
from lecturepilot.bounded_sampling import evenly_sampled_indexes
from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.compiled_slide_canvas import compiled_slide_preview
from lecturepilot.latex_canvas_importer import CANVAS_IMPORT_VERSION, import_latex_canvas
from lecturepilot.latex_canvas_text import BROWSER_ASSET_SUFFIXES, slug
from lecturepilot.pdf_extract import pdf_page_count, read_pdf_text
from lecturepilot.pdf_slide_assets import PdfSlideAssetError, render_pdf_slide_blocks
from lecturepilot.source_bundle import SourceBundleFile, scan_source_bundle
from lecturepilot.source_bundle_latex import scoped_latex_sections, source_kind
from lecturepilot.source_bundle_media import asset_section, media_caption, video_section
from lecturepilot.source_code_canvas import SourceCodeCanvasError, code_section, notebook_section


MAX_TEXT_CHARS_PER_FILE = 12000
MAX_PDF_PAGES = 20
MAX_PDF_TEXT_BLOCKS = 12
VIDEO_SUFFIXES = {".mp4", ".webm", ".mov", ".mkv", ".avi"}


class SourceBundleCanvasError(RuntimeError):
    """Raised when uploaded source material cannot produce planner evidence."""


def import_source_bundle_canvas(
    *,
    source_root: Path,
    course_id: str,
    lecture_id: str,
    workspace_path: str,
    files: list[SourceBundleFile] | None = None,
    derived_root: Path | None = None,
    compiled_slide_pdf: Path | None = None,
    compiled_slide_source_ref: str | None = None,
    warnings: list[str] | None = None,
) -> CanvasDocument:
    files = files if files is not None else scan_source_bundle(source_root)
    derived_root = derived_root or source_root
    sections: list[CanvasSection] = []
    source_refs: list[str] = []
    document_warnings = list(warnings or [])
    for file in files:
        path = source_root / file.path
        if file.kind == "latex":
            latex = import_latex_canvas(
                source_path=path,
                material_root=path.parent,
                course_id=course_id,
                lecture_id=lecture_id,
                workspace_path=workspace_path,
                derived_root=derived_root,
                include_matching_pdf_slides=False,
            )
            sections.extend(scoped_latex_sections(latex.sections, file.path))
            document_warnings.extend(latex.warnings)
            source_refs.append(file.path)
        elif file.kind in {"markdown", "text"}:
            if section := _text_section(path, file.path, kind=file.kind):
                sections.append(section)
                source_refs.append(file.path)
        elif file.kind == "pdf":
            if section := _pdf_section(
                path,
                file.path,
                source_root,
                derived_root,
                course_id,
                lecture_id,
            ):
                sections.append(section)
                source_refs.append(file.path)
        elif file.kind == "notebook":
            try:
                section = notebook_section(path, file.path)
            except SourceCodeCanvasError as exc:
                raise SourceBundleCanvasError(str(exc)) from exc
            if section:
                sections.append(section)
                source_refs.append(file.path)
        elif file.kind == "code":
            try:
                section = code_section(path, file.path)
            except SourceCodeCanvasError as exc:
                raise SourceBundleCanvasError(str(exc)) from exc
            if section:
                sections.append(section)
                source_refs.append(file.path)
        elif file.kind in {"image", "svg"} and path.suffix.lower() in BROWSER_ASSET_SUFFIXES:
            sections.append(asset_section(file.path, source_root, course_id, lecture_id))
        elif file.kind == "video" and path.suffix.lower() in VIDEO_SUFFIXES:
            sections.append(video_section(file.path, source_root, course_id, lecture_id))

    if compiled_slide_pdf and compiled_slide_source_ref:
        preview, warning = compiled_slide_preview(
            pdf_path=compiled_slide_pdf,
            output_root=derived_root,
            course_id=course_id,
            lecture_id=lecture_id,
            source_ref=compiled_slide_source_ref,
        )
        if preview:
            sections.append(preview)
        if warning:
            document_warnings.append(warning)

    if not any(_has_text(section) for section in sections):
        raise SourceBundleCanvasError(
            "No readable LaTeX, Markdown, text, PDF, notebook, or code source material found."
        )
    return CanvasDocument(
        id=f"{course_id}-{lecture_id}",
        import_version=CANVAS_IMPORT_VERSION,
        course_id=course_id,
        lecture_id=lecture_id,
        title=_title_from_sections(sections),
        source_kind=source_kind(source_refs),
        source_ref=", ".join(source_refs[:8]) or "source bundle",
        workspace_path=workspace_path,
        sections=_dedupe_sections(sections),
        warnings=list(dict.fromkeys(document_warnings))[:20],
    )


def _text_section(path: Path, source_ref: str, *, kind: str) -> CanvasSection | None:
    text = path.read_text(encoding="utf-8", errors="replace")
    blocks = _text_blocks(source_ref, text)
    if not blocks:
        return None
    title = _heading(text) or path.stem.replace("-", " ").replace("_", " ").title()
    return CanvasSection(
        id=slug(source_ref),
        title=title[:200],
        source_ref=source_ref,
        blocks=blocks,
    )


def _pdf_section(
    path: Path,
    source_ref: str,
    source_root: Path,
    derived_root: Path,
    course_id: str,
    lecture_id: str,
) -> CanvasSection | None:
    text = _pdf_text(path)
    page_numbers = [
        index + 1 for index in evenly_sampled_indexes(_pdf_page_count(path), MAX_PDF_PAGES)
    ]
    section_id = slug(source_ref)
    caption = media_caption(source_root, source_ref)
    blocks = _pdf_text_blocks(source_ref, text)
    blocks.append(
        CanvasBlock(
            id=f"{section_id}-asset-1",
            type="asset",
            asset_path=source_ref,
            asset_url=f"/course-assets/{course_id}/{lecture_id}/{source_ref}",
            caption=caption,
        )
    )
    try:
        blocks.extend(
            render_pdf_slide_blocks(
                pdf_path=path,
                source_root=source_root,
                output_root=derived_root,
                course_id=course_id,
                lecture_id=lecture_id,
                source_ref=source_ref,
            )
        )
    except PdfSlideAssetError as exc:
        raise SourceBundleCanvasError(str(exc)) from exc
    return CanvasSection(
        id=section_id,
        title=path.stem.replace("-", " ").replace("_", " ").title()[:200],
        source_ref=f"{source_ref} pages {', '.join(map(str, page_numbers))}",
        blocks=blocks,
    )


def _text_blocks(source_ref: str, text: str) -> list[CanvasBlock]:
    paragraphs = _paragraphs(text)
    return [
        CanvasBlock(
            id=f"{slug(source_ref)}-p-{index}",
            type="paragraph",
            text=paragraph,
        )
        for index, paragraph in enumerate(paragraphs[:8], start=1)
    ]


def _pdf_text_blocks(source_ref: str, text: str) -> list[CanvasBlock]:
    paragraphs = _paragraphs(text)
    selected = [
        paragraphs[index] for index in evenly_sampled_indexes(len(paragraphs), MAX_PDF_TEXT_BLOCKS)
    ]
    return [
        CanvasBlock(id=f"{slug(source_ref)}-p-{index}", type="paragraph", text=paragraph)
        for index, paragraph in enumerate(selected, start=1)
    ]


def _paragraphs(text: str) -> list[str]:
    cleaned = _strip_markdown_noise(text)[:MAX_TEXT_CHARS_PER_FILE]
    paragraphs = []
    for chunk in cleaned.split("\n\n"):
        paragraph = " ".join(line.strip() for line in chunk.splitlines() if line.strip())
        if len(paragraph.split()) >= 5:
            paragraphs.append(paragraph[:1800])
    return paragraphs


def _strip_markdown_noise(text: str) -> str:
    lines = []
    for line in text.replace("\r\n", "\n").splitlines():
        stripped = line.strip()
        if stripped.startswith("<!--"):
            continue
        lines.append(stripped.lstrip("# ").lstrip("> ").lstrip("-* "))
    return "\n".join(lines)


def _heading(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("# ").strip()
    return None


def _pdf_text(path: Path) -> str:
    try:
        return read_pdf_text(
            str(path),
            max_pages=MAX_PDF_PAGES,
            max_chars=MAX_TEXT_CHARS_PER_FILE,
        )
    except (BoundedProcessingError, ImportError) as exc:
        raise SourceBundleCanvasError("PDF text extraction failed safely.") from exc


def _pdf_page_count(path: Path) -> int:
    try:
        return pdf_page_count(str(path))
    except (BoundedProcessingError, ImportError) as exc:
        raise SourceBundleCanvasError("PDF page inspection failed safely.") from exc


def _has_text(section: CanvasSection) -> bool:
    return any(block.text or block.items for block in section.blocks)


def _title_from_sections(sections: list[CanvasSection]) -> str:
    for section in sections:
        if _has_text(section):
            return section.title
    return "Uploaded course material"


def _dedupe_sections(sections: list[CanvasSection]) -> list[CanvasSection]:
    seen: dict[str, int] = {}
    result = []
    for section in sections:
        seen[section.id] = seen.get(section.id, 0) + 1
        result.append(
            section.model_copy(
                update={
                    "id": section.id
                    if seen[section.id] == 1
                    else f"{section.id}-{seen[section.id]}"
                }
            )
        )
    return result
