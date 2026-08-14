from __future__ import annotations

import os
from pathlib import Path

from lecturepilot.document_converter_client import (
    DocumentConverterClient,
    DocumentConverterError,
)
from lecturepilot.source_bundle import SourceBundleFile


NORMALIZABLE_KINDS = {"document", "presentation", "spreadsheet"}


def normalize_selected_documents(
    *,
    files: list[SourceBundleFile],
    source_root: Path,
    normalized_root: Path,
) -> None:
    selected = [file for file in files if file.kind in NORMALIZABLE_KINDS]
    if not selected:
        return
    configured = os.getenv("LECTUREPILOT_DOCUMENT_CONVERTER_URL", "").strip()
    if not configured:
        raise DocumentConverterError("Document converter is not configured.")
    client = DocumentConverterClient(configured)
    for file in selected:
        if not file.sha256:
            raise DocumentConverterError(f"Source revision is unavailable for {file.path}.")
        client.convert(
            path=source_root / file.path,
            source_path=file.path,
            sha256=file.sha256,
            normalized_root=normalized_root,
        )
