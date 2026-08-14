from __future__ import annotations

from pathlib import Path

from lecturepilot.course_source_routing_models import (
    CourseSourceRoute,
    CourseSourceRoutingManifest,
    SourceProcessingStatus,
)
from lecturepilot.pdf_extract import pdf_requires_ocr
from lecturepilot.source_normalization_store import (
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
    if route.kind == "pdf" and pdf_requires_ocr(str(source_root / route.path)):
        return SourceProcessingStatus.OCR_NEEDED
    return SourceProcessingStatus.PRESERVED
