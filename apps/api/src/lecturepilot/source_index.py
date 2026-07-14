from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

from pydantic import ValidationError

from lecturepilot.durable_files import ensure_durable_directory, fsync_directory
from lecturepilot.source_bundle import SourceBundleFile, scan_source_bundle
from lecturepilot.source_index_models import CourseSourceIndex, IndexedSourceFile
from lecturepilot.storage_layout import StorageLayout


HASH_CHUNK_BYTES = 1024 * 1024


def indexed_course_files(
    *,
    layout: StorageLayout,
    course_id: str,
    known_hashes: dict[str, str] | None = None,
) -> list[SourceBundleFile]:
    index = refresh_course_source_index(
        course_id=course_id,
        uploads_dir=layout.course_uploads_dir(course_id),
        index_path=layout.course_source_index_path(course_id),
        known_hashes=known_hashes,
    )
    return [item.as_bundle_file() for item in index.files]


def refresh_course_source_index(
    *,
    course_id: str,
    uploads_dir: Path,
    index_path: Path,
    known_hashes: dict[str, str] | None = None,
) -> CourseSourceIndex:
    existing = _read_index(index_path, course_id)
    previous = {item.path: item for item in existing.files} if existing else {}
    known_hashes = known_hashes or {}
    files = [
        _indexed_file(uploads_dir, item, previous.get(item.path), known_hashes.get(item.path))
        for item in scan_source_bundle(uploads_dir)
    ]
    index = CourseSourceIndex(course_id=course_id, files=files)
    if existing != index:
        _write_index(index_path, index)
    return index


def _indexed_file(
    uploads_dir: Path,
    item: SourceBundleFile,
    previous: IndexedSourceFile | None,
    known_hash: str | None,
) -> IndexedSourceFile:
    path = uploads_dir / item.path
    modified_ns = path.stat().st_mtime_ns
    unchanged = (
        previous is not None
        and previous.kind == item.kind
        and previous.size_bytes == item.size_bytes
        and previous.modified_ns == modified_ns
    )
    # Uploads supply their one-pass hash; unchanged files reuse the persisted hash.
    digest = known_hash or (previous.sha256 if unchanged else _sha256(path))
    return IndexedSourceFile(
        path=item.path,
        kind=item.kind,
        size_bytes=item.size_bytes,
        sha256=digest,
        modified_ns=modified_ns,
    )


def _read_index(path: Path, course_id: str) -> CourseSourceIndex | None:
    if not path.exists():
        return None
    try:
        index = CourseSourceIndex.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError):
        return None
    return index if index.course_id == course_id else None


def _write_index(path: Path, index: CourseSourceIndex) -> None:
    ensure_durable_directory(path.parent)
    descriptor, temporary = tempfile.mkstemp(prefix=".source-index-", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(index.model_dump_json(indent=2))
            handle.flush()
            os.fsync(handle.fileno())
        temporary_path.replace(path)
        fsync_directory(path.parent)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(HASH_CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()
