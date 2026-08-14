from __future__ import annotations

import json
from pathlib import Path

from lecturepilot_converter.docling_blocks import docling_blocks
from lecturepilot_converter.office_pptx import pptx_supplemental_blocks
from lecturepilot_converter.office_render import render_office_pdf
from lecturepilot_converter.office_xlsx import xlsx_table_blocks
from lecturepilot_converter.presentation_ocr import ocr_presentation_pages


MEDIA_TYPES = {
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


class DocumentConversionError(RuntimeError):
    pass


def convert_document(
    source: Path,
    *,
    source_path: str,
    source_sha256: str,
    output_root: Path,
) -> dict:
    suffix = source.suffix.lower()
    if suffix not in MEDIA_TYPES:
        raise DocumentConversionError(f"Unsupported document format: {suffix or '<none>'}.")
    document = _convert_with_docling_backend(source, suffix=suffix)
    blocks = docling_blocks(document.export_to_dict(), suffix=suffix)
    if suffix == ".pptx":
        blocks.extend(pptx_supplemental_blocks(source))
    elif suffix == ".xlsx":
        blocks = xlsx_table_blocks(source)
    warnings = []
    revision_root = output_root / source_sha256
    if suffix == ".pptx":
        rendered = revision_root / "rendered.pdf"
        render_office_pdf(source, rendered)
        ocr_blocks, warnings = ocr_presentation_pages(rendered, blocks)
        blocks.extend(ocr_blocks)
    manifest = {
        "schema_version": 1,
        "source_path": source_path,
        "source_sha256": source_sha256,
        "media_type": MEDIA_TYPES[suffix],
        "blocks": blocks,
        "warnings": warnings,
    }
    _write_outputs(
        revision_root,
        manifest=manifest,
        markdown=document.export_to_markdown().strip(),
    )
    return manifest


def _convert_with_docling_backend(source: Path, *, suffix: str):
    from docling.backend.msexcel_backend import MsExcelDocumentBackend
    from docling.backend.mspowerpoint_backend import MsPowerpointDocumentBackend
    from docling.backend.msword_backend import MsWordDocumentBackend
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.document import InputDocument

    backend, input_format = {
        ".docx": (MsWordDocumentBackend, InputFormat.DOCX),
        ".pptx": (MsPowerpointDocumentBackend, InputFormat.PPTX),
        ".xlsx": (MsExcelDocumentBackend, InputFormat.XLSX),
    }[suffix]
    input_document = InputDocument(source, format=input_format, backend=backend)
    if not input_document.valid:
        raise DocumentConversionError("Document structure could not be parsed safely.")
    return input_document._backend.convert()


def _write_outputs(revision_root: Path, *, manifest: dict, markdown: str) -> None:
    revision_root.mkdir(parents=True, exist_ok=True)
    (revision_root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    (revision_root / "content.md").write_text(markdown, encoding="utf-8")
