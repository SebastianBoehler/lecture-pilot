from __future__ import annotations

import re
from pathlib import Path
from pathlib import PurePosixPath

from lecturepilot.pdf_extract import read_pdf_text
from lecturepilot.source_bundle import SourceBundleFile
from lecturepilot.source_index_models import IndexedSourceFile
from lecturepilot.source_normalization_store import (
    SourceNormalizationError,
    load_normalized_document,
)


MAX_EXCERPT_CHARS = 900
TEXT_KINDS = {"code", "json", "latex", "markdown", "notebook", "python", "text"}
NORMALIZED_KINDS = {"document", "presentation", "spreadsheet"}
DETAIL_KINDS = {*TEXT_KINDS, *NORMALIZED_KINDS, "pdf", "video"}
PRIORITY_DETAIL_KINDS = {"code", "notebook", "python", "video"}
MAX_SELECTION_DETAILS = 60


def source_file_excerpt(item: IndexedSourceFile, roots: list[Path]) -> str:
    if item.kind in NORMALIZED_KINDS:
        if excerpt := normalized_source_excerpt(item, roots, max_chars=MAX_EXCERPT_CHARS):
            return excerpt
    path = _resolve_source(item.path, roots)
    if path is None:
        return "file contents unavailable"
    try:
        if item.kind == "pdf":
            return _compact(read_pdf_text(str(path), max_pages=3, max_chars=MAX_EXCERPT_CHARS))
        if item.kind in TEXT_KINDS:
            with path.open("r", encoding="utf-8", errors="ignore") as handle:
                return _compact(handle.read(MAX_EXCERPT_CHARS * 2))
    except (OSError, RuntimeError, ValueError):
        return "text extraction unavailable; use path and file metadata"
    return "binary asset; use path and surrounding course structure"


def normalized_source_excerpt(
    item: IndexedSourceFile | SourceBundleFile, roots: list[Path], *, max_chars: int
) -> str | None:
    if not item.sha256:
        return None
    for root in roots:
        try:
            document = load_normalized_document(root, item.sha256)
        except SourceNormalizationError:
            continue
        values = []
        for block in document.blocks:
            if block.text:
                values.append(block.text)
            values.extend(
                str(cell.value if cell.value is not None else cell.formula)
                for cell in block.cells
                if cell.value is not None or cell.formula
            )
        return _compact(" ".join(values))[:max_chars]
    return None


def selection_detail_files(
    files: list[IndexedSourceFile], primary_paths: set[str]
) -> list[IndexedSourceFile]:
    candidates = [
        item for item in files if item.path not in primary_paths and item.kind in DETAIL_KINDS
    ]
    prioritized = sorted(
        (item for item in candidates if item.kind in PRIORITY_DETAIL_KINDS),
        key=_detail_priority,
    )[:MAX_SELECTION_DETAILS]
    prioritized_paths = {item.path for item in prioritized}
    by_kind: dict[str, list[IndexedSourceFile]] = {}
    for item in sorted(candidates, key=_detail_priority):
        if item.path in prioritized_paths:
            continue
        by_kind.setdefault(item.kind, []).append(item)
    selected = list(prioritized)
    kinds = sorted(by_kind)
    while len(selected) < MAX_SELECTION_DETAILS and kinds:
        remaining = []
        for kind in kinds:
            bucket = by_kind[kind]
            if bucket and len(selected) < MAX_SELECTION_DETAILS:
                selected.append(bucket.pop(0))
            if bucket:
                remaining.append(kind)
        kinds = remaining
    return selected


def _detail_priority(item: IndexedSourceFile) -> tuple[int, int, str]:
    return (
        len(PurePosixPath(item.path).parts),
        -item.size_bytes,
        item.path.casefold(),
    )


def _resolve_source(relative_path: str, roots: list[Path]) -> Path | None:
    for root in roots:
        candidate = root / relative_path
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def _compact(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()[:MAX_EXCERPT_CHARS] or "no text extracted"
