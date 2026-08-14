from __future__ import annotations

from pathlib import Path, PurePosixPath

from lecturepilot.canvas_models import CanvasDocument, CanvasSection
from lecturepilot.compiled_slide_canvas import compiled_slide_preview
from lecturepilot.latex_canvas_importer import CANVAS_IMPORT_VERSION, import_latex_canvas
from lecturepilot.latex_canvas_text import BROWSER_ASSET_SUFFIXES, slug
from lecturepilot.source_bundle import SourceBundleFile, scan_source_bundle
from lecturepilot.source_bundle_latex import scoped_latex_sections, source_kind
from lecturepilot.source_bundle_media import asset_section, video_section
from lecturepilot.source_bundle_normalized import NormalizedCanvasError, normalized_sections
from lecturepilot.source_bundle_pdf import PdfSourceError, pdf_sections
from lecturepilot.source_bundle_text import heading, text_blocks
from lecturepilot.source_bundle_table import SourceTableError, csv_section
from lecturepilot.source_code_canvas import SourceCodeCanvasError, code_section, notebook_section


VIDEO_SUFFIXES = {".mp4", ".webm", ".mov", ".mkv", ".avi"}
MAX_SOURCE_REF_CHARS = 500


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
    source_paths = {file.path for file in files}
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
            try:
                imported_pdf_sections = pdf_sections(
                    path=path,
                    source_ref=file.path,
                    source_root=source_root,
                    derived_root=derived_root,
                    course_id=course_id,
                    lecture_id=lecture_id,
                )
            except PdfSourceError as exc:
                raise SourceBundleCanvasError(str(exc)) from exc
            if imported_pdf_sections:
                sections.extend(imported_pdf_sections)
                source_refs.append(file.path)
        elif file.kind == "notebook":
            try:
                section = notebook_section(path, file.path)
            except SourceCodeCanvasError as exc:
                raise SourceBundleCanvasError(str(exc)) from exc
            if section:
                sections.append(section)
                source_refs.append(file.path)
        elif file.kind in {"code", "json"} and not _is_media_sidecar(file.path, source_paths):
            try:
                section = code_section(path, file.path)
            except SourceCodeCanvasError as exc:
                raise SourceBundleCanvasError(str(exc)) from exc
            if section:
                sections.append(section)
                source_refs.append(file.path)
        elif file.kind == "table":
            try:
                section = csv_section(path, file.path)
            except SourceTableError as exc:
                raise SourceBundleCanvasError(str(exc)) from exc
            if section:
                sections.append(section)
                source_refs.append(file.path)
        elif file.kind in {"document", "presentation", "spreadsheet"}:
            try:
                imported_sections, normalized_warnings = normalized_sections(
                    file=file,
                    normalized_root=derived_root,
                    course_id=course_id,
                    lecture_id=lecture_id,
                )
            except NormalizedCanvasError as exc:
                raise SourceBundleCanvasError(str(exc)) from exc
            if imported_sections:
                sections.extend(imported_sections)
                source_refs.append(file.path)
            document_warnings.extend(normalized_warnings)
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
            "No readable document, slide, spreadsheet, LaTeX, Markdown, text, PDF, notebook, "
            "or code source material found."
        )
    return CanvasDocument(
        id=f"{course_id}-{lecture_id}",
        import_version=CANVAS_IMPORT_VERSION,
        course_id=course_id,
        lecture_id=lecture_id,
        title=_title_from_sections(sections),
        source_kind=source_kind(source_refs),
        source_ref=_compact_source_ref(source_refs),
        workspace_path=workspace_path,
        sections=_dedupe_sections(sections),
        warnings=list(dict.fromkeys(document_warnings))[:20],
    )


def _text_section(path: Path, source_ref: str, *, kind: str) -> CanvasSection | None:
    text = path.read_text(encoding="utf-8", errors="replace")
    blocks = text_blocks(source_ref, text)
    if not blocks:
        return None
    title = heading(text) or path.stem.replace("-", " ").replace("_", " ").title()
    return CanvasSection(
        id=slug(source_ref),
        title=title[:200],
        source_ref=source_ref,
        blocks=blocks,
    )


def _compact_source_ref(source_refs: list[str]) -> str:
    if not source_refs:
        return "source bundle"
    visible = source_refs[:8]
    joined = ", ".join(visible)
    if len(joined) <= MAX_SOURCE_REF_CHARS:
        return joined
    for count in range(len(visible) - 1, 0, -1):
        suffix = f", … ({len(source_refs) - count} more sources)"
        candidate = f"{', '.join(visible[:count])}{suffix}"
        if len(candidate) <= MAX_SOURCE_REF_CHARS:
            return candidate
    if len(source_refs) == 1:
        return f"{source_refs[0][: MAX_SOURCE_REF_CHARS - 1]}…"
    suffix = f" … ({len(source_refs) - 1} more sources)"
    return f"{source_refs[0][: MAX_SOURCE_REF_CHARS - len(suffix)]}{suffix}"


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


def _is_media_sidecar(path: str, source_paths: set[str]) -> bool:
    source = PurePosixPath(path)
    if source.suffix.lower() != ".json":
        return False
    without_json = source.with_suffix("")
    if without_json.as_posix() in source_paths:
        return True
    media_suffixes = {*BROWSER_ASSET_SUFFIXES, *VIDEO_SUFFIXES}
    return any(
        without_json.with_suffix(suffix).as_posix() in source_paths for suffix in media_suffixes
    )
