from __future__ import annotations

import json
from pathlib import Path

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.latex_canvas_importer import CANVAS_IMPORT_VERSION, import_latex_canvas
from lecturepilot.latex_canvas_text import BROWSER_ASSET_SUFFIXES, slug
from lecturepilot.pdf_slide_assets import PdfSlideAssetError, render_pdf_slide_blocks
from lecturepilot.source_bundle import scan_source_bundle


MAX_TEXT_CHARS_PER_FILE = 12000
MAX_PDF_PAGES = 20
VIDEO_SUFFIXES = {".mp4", ".webm", ".mov", ".mkv", ".avi"}


class SourceBundleCanvasError(RuntimeError):
    """Raised when uploaded source material cannot produce planner evidence."""


def import_source_bundle_canvas(
    *,
    source_root: Path,
    course_id: str,
    lecture_id: str,
    workspace_path: str,
) -> CanvasDocument:
    files = scan_source_bundle(source_root)
    sections: list[CanvasSection] = []
    source_refs: list[str] = []
    for file in files:
        path = source_root / file.path
        if file.kind == "latex":
            latex = import_latex_canvas(
                source_path=path,
                material_root=source_root,
                course_id=course_id,
                lecture_id=lecture_id,
                workspace_path=workspace_path,
            )
            sections.extend(_scoped_latex_sections(latex.sections, file.path))
            source_refs.append(file.path)
        elif file.kind in {"markdown", "text"}:
            if section := _text_section(path, file.path, kind=file.kind):
                sections.append(section)
                source_refs.append(file.path)
        elif file.kind == "pdf":
            if section := _pdf_section(path, file.path, source_root, course_id, lecture_id):
                sections.append(section)
                source_refs.append(file.path)
        elif file.kind in {"image", "svg"} and path.suffix.lower() in BROWSER_ASSET_SUFFIXES:
            sections.append(_asset_section(file.path, source_root, course_id, lecture_id))
        elif file.kind == "video" and path.suffix.lower() in VIDEO_SUFFIXES:
            sections.append(_video_section(file.path, source_root, course_id, lecture_id))

    if not any(_has_text(section) for section in sections):
        raise SourceBundleCanvasError("No readable .tex, .md, .txt, or .pdf source material found.")
    return CanvasDocument(
        id=f"{course_id}-{lecture_id}",
        import_version=CANVAS_IMPORT_VERSION,
        course_id=course_id,
        lecture_id=lecture_id,
        title=_title_from_sections(sections),
        source_kind="markdown",
        source_ref=", ".join(source_refs[:8]) or "source bundle",
        workspace_path=workspace_path,
        sections=_dedupe_sections(sections),
    )


def _scoped_latex_sections(sections: list[CanvasSection], path: str) -> list[CanvasSection]:
    prefix = slug(Path(path).stem)
    result = []
    for section in sections:
        result.append(
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
        )
    return result


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


def _pdf_section(path: Path, source_ref: str, source_root: Path, course_id: str, lecture_id: str) -> CanvasSection | None:
    text = _pdf_text(path)
    section_id = slug(source_ref)
    caption = _media_caption(source_root, source_ref)
    blocks = _text_blocks(source_ref, text)
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
            render_pdf_slide_blocks(pdf_path=path, source_root=source_root, course_id=course_id, lecture_id=lecture_id, source_ref=source_ref)
        )
    except PdfSlideAssetError as exc:
        raise SourceBundleCanvasError(str(exc)) from exc
    return CanvasSection(
        id=section_id,
        title=path.stem.replace("-", " ").replace("_", " ").title()[:200],
        source_ref=f"{source_ref} pages 1-{min(MAX_PDF_PAGES, _pdf_page_count(path))}",
        blocks=blocks,
    )


def _asset_section(path: str, source_root: Path, course_id: str, lecture_id: str) -> CanvasSection:
    section_id = slug(f"asset {path}")
    caption = _media_caption(source_root, path)
    return CanvasSection(
        id=section_id,
        title=_media_title(path, caption),
        source_ref=path,
        blocks=[
            CanvasBlock(
                id=f"{section_id}-asset-1",
                type="asset",
                asset_path=path,
                asset_url=f"/course-assets/{course_id}/{lecture_id}/{path}",
                caption=caption,
            )
        ],
    )


def _video_section(path: str, source_root: Path, course_id: str, lecture_id: str) -> CanvasSection:
    section_id = slug(f"video {path}")
    caption = _media_caption(source_root, path)
    return CanvasSection(
        id=section_id,
        title=_media_title(path, caption),
        source_ref=path,
        blocks=[
            CanvasBlock(
                id=f"{section_id}-video-1",
                type="video",
                asset_path=path,
                asset_url=f"/course-assets/{course_id}/{lecture_id}/{path}",
                caption=caption,
            )
        ],
    )


def _media_caption(source_root: Path, path: str) -> str:
    metadata = _metadata(source_root / path)
    if metadata:
        title = _metadata_value(metadata, "title", "caption", "alt") or _filename_title(path)
        details = _metadata_value(metadata, "description", "summary")
        tags = metadata.get("tags")
        tag_text = ", ".join(str(tag).strip() for tag in tags[:8] if str(tag).strip()) if isinstance(tags, list) else ""
        return " - ".join(part for part in [title, details, tag_text] if part)[:500]
    return _filename_title(path)[:500]


def _metadata(path: Path) -> dict | None:
    for candidate in (path.with_suffix(path.suffix + ".json"), path.with_suffix(".json")):
        if candidate.exists() and candidate.stat().st_size <= 32_000:
            try:
                payload = json.loads(candidate.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError, UnicodeDecodeError):
                continue
            if isinstance(payload, dict):
                return payload
    return None


def _metadata_value(metadata: dict, *keys: str) -> str:
    for key in keys:
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _media_title(path: str, caption: str) -> str:
    return (caption.split(" - ", 1)[0] or _filename_title(path))[:200]


def _filename_title(path: str) -> str:
    return Path(path).stem.replace("-", " ").replace("_", " ").title()


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
        import fitz
    except ImportError as exc:
        raise SourceBundleCanvasError("PyMuPDF is required to read PDF source material.") from exc
    document = fitz.open(path)
    try:
        pages = [document.load_page(index).get_text("text") for index in range(min(len(document), MAX_PDF_PAGES))]
        return "\n\n".join(pages)
    finally:
        document.close()


def _pdf_page_count(path: Path) -> int:
    try:
        import fitz
    except ImportError as exc:
        raise SourceBundleCanvasError("PyMuPDF is required to read PDF source material.") from exc
    document = fitz.open(path)
    try:
        return len(document)
    finally:
        document.close()


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
                update={"id": section.id if seen[section.id] == 1 else f"{section.id}-{seen[section.id]}"}
            )
        )
    return result
