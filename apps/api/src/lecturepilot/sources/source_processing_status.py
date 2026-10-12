from __future__ import annotations

import json
from pathlib import Path

from lecturepilot.sources.course_source_routing_models import (
    CourseSourceRoute,
    CourseSourceRoutingManifest,
    SourceProcessingStatus,
)
from lecturepilot.core.durable_files import atomic_write_json
from lecturepilot.sources.pdf_extract import pdf_requires_ocr
from lecturepilot.sources.source_normalization_store import (
    SourceNormalizationError,
    load_normalized_document,
)


NORMALIZED_KINDS = {"document", "presentation", "spreadsheet"}


def with_processing_status(
    manifest: CourseSourceRoutingManifest,
    *,
    source_root: Path,
    normalized_root: Path,
) -> CourseSourceRoutingManifest:
    routes = [
        route.model_copy(
            update={
                "processing_status": _status(
                    route,
                    source_root=source_root,
                    normalized_root=normalized_root,
                )
            }
        )
        for route in manifest.routes
    ]
    return manifest.model_copy(update={"routes": routes})


def _status(
    route: CourseSourceRoute,
    *,
    source_root: Path,
    normalized_root: Path,
) -> SourceProcessingStatus:
    if route.kind in NORMALIZED_KINDS:
        try:
            document = load_normalized_document(normalized_root, route.sha256)
        except SourceNormalizationError:
            return SourceProcessingStatus.PRESERVED
        if any(warning.startswith("OCR required") for warning in document.warnings):
            return SourceProcessingStatus.OCR_NEEDED
        return SourceProcessingStatus.CONVERTED
    if route.kind == "pdf" and _pdf_needs_ocr(route, source_root, normalized_root):
        return SourceProcessingStatus.OCR_NEEDED
    return SourceProcessingStatus.PRESERVED


def _pdf_needs_ocr(route: CourseSourceRoute, source_root: Path, normalized_root: Path) -> bool:
    """Triage opens and samples the PDF, so cache it by content hash for every later view."""
    cached = normalized_root / "ocr-triage" / f"{route.sha256}.json"
    try:
        return bool(json.loads(cached.read_text(encoding="utf-8"))["ocr_needed"])
    except (OSError, ValueError, KeyError, TypeError):
        pass
    needed = pdf_requires_ocr(str(source_root / route.path))
    atomic_write_json(cached, {"ocr_needed": needed})
    return needed
