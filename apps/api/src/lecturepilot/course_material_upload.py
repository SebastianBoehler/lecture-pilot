from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile

from lecturepilot.workspace import WorkspacePolicyError


UPLOAD_CHUNK_BYTES = 1024 * 1024


@dataclass(frozen=True)
class StoredCourseMaterial:
    size_bytes: int
    sha256: str


async def store_course_material(
    *,
    upload: UploadFile,
    target: Path,
    max_bytes: int,
) -> StoredCourseMaterial:
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".upload-", dir=target.parent)
    temporary_path = Path(temporary)
    digest = hashlib.sha256()
    size_bytes = 0
    try:
        with os.fdopen(descriptor, "wb") as handle:
            while chunk := await upload.read(UPLOAD_CHUNK_BYTES):
                size_bytes += len(chunk)
                if size_bytes > max_bytes:
                    raise WorkspacePolicyError(
                        f"{target.suffix.lower()} files are limited to {max_bytes} bytes."
                    )
                digest.update(chunk)
                handle.write(chunk)
            handle.flush()
            os.fsync(handle.fileno())
        temporary_path.replace(target)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise
    return StoredCourseMaterial(size_bytes=size_bytes, sha256=digest.hexdigest())
