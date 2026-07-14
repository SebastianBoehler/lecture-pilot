from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
import stat
import zipfile

from lecturepilot_latex_compiler.errors import (
    ARCHIVE_LIMIT,
    INVALID_ARCHIVE,
    CompilerServiceError,
)
from lecturepilot_latex_compiler.limits import (
    MAX_ARCHIVE_BYTES,
    MAX_COMPRESSION_RATIO,
    MAX_EXPANDED_BYTES,
    MAX_FILE_BYTES,
    MAX_FILES,
    MAX_PATH_BYTES,
    MAX_PATH_PARTS,
)


_ALLOWED_COMPRESSION = {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}


def extract_source_archive(archive_path: Path, destination: Path) -> None:
    if not archive_path.is_file() or archive_path.stat().st_size > MAX_ARCHIVE_BYTES:
        raise CompilerServiceError("archive_limit", ARCHIVE_LIMIT, status=413)
    destination.mkdir(mode=0o700, parents=True, exist_ok=False)
    try:
        with zipfile.ZipFile(archive_path) as archive:
            entries = archive.infolist()
            _validate_entries(entries)
            _extract_entries(archive, entries, destination)
    except CompilerServiceError:
        raise
    except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile) as exc:
        raise CompilerServiceError(
            "invalid_archive", INVALID_ARCHIVE, status=400
        ) from exc


def safe_relative_path(value: str) -> PurePosixPath:
    if not value or "\x00" in value or "\\" in value:
        raise CompilerServiceError("invalid_archive", INVALID_ARCHIVE, status=400)
    if len(value.encode("utf-8")) > MAX_PATH_BYTES:
        raise CompilerServiceError("archive_limit", ARCHIVE_LIMIT, status=413)
    path = PurePosixPath(value)
    if path.is_absolute() or len(path.parts) > MAX_PATH_PARTS:
        raise CompilerServiceError("invalid_archive", INVALID_ARCHIVE, status=400)
    if not path.parts or any(
        part in {"", ".", ".."} or part.startswith(".") for part in path.parts
    ):
        raise CompilerServiceError("invalid_archive", INVALID_ARCHIVE, status=400)
    if any(any(ord(character) < 32 for character in part) for part in path.parts):
        raise CompilerServiceError("invalid_archive", INVALID_ARCHIVE, status=400)
    return path


def _validate_entries(entries: list[zipfile.ZipInfo]) -> None:
    if not entries or len(entries) > MAX_FILES:
        raise CompilerServiceError("archive_limit", ARCHIVE_LIMIT, status=413)
    expanded = 0
    seen: set[str] = set()
    for entry in entries:
        path = safe_relative_path(entry.filename.rstrip("/"))
        canonical = path.as_posix().casefold()
        if canonical in seen:
            raise CompilerServiceError("invalid_archive", INVALID_ARCHIVE, status=400)
        seen.add(canonical)
        if entry.flag_bits & 0x1 or entry.compress_type not in _ALLOWED_COMPRESSION:
            raise CompilerServiceError("invalid_archive", INVALID_ARCHIVE, status=400)
        mode = entry.external_attr >> 16
        file_type = stat.S_IFMT(mode)
        if file_type == stat.S_IFLNK or file_type not in {
            0,
            stat.S_IFREG,
            stat.S_IFDIR,
        }:
            raise CompilerServiceError("invalid_archive", INVALID_ARCHIVE, status=400)
        if entry.file_size > MAX_FILE_BYTES:
            raise CompilerServiceError("archive_limit", ARCHIVE_LIMIT, status=413)
        expanded += entry.file_size
        if expanded > MAX_EXPANDED_BYTES:
            raise CompilerServiceError("archive_limit", ARCHIVE_LIMIT, status=413)
        ratio = entry.file_size / max(1, entry.compress_size)
        if entry.file_size > 1024 * 1024 and ratio > MAX_COMPRESSION_RATIO:
            raise CompilerServiceError("archive_limit", ARCHIVE_LIMIT, status=413)


def _extract_entries(
    archive: zipfile.ZipFile,
    entries: list[zipfile.ZipInfo],
    destination: Path,
) -> None:
    expanded = 0
    for entry in entries:
        relative = safe_relative_path(entry.filename.rstrip("/"))
        target = destination.joinpath(*relative.parts)
        if entry.is_dir():
            target.mkdir(mode=0o700, parents=True, exist_ok=True)
            continue
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(target, flags, 0o600)
        try:
            with archive.open(entry) as source, os.fdopen(descriptor, "wb") as output:
                descriptor = -1
                while chunk := source.read(1024 * 1024):
                    expanded += len(chunk)
                    if (
                        expanded > MAX_EXPANDED_BYTES
                        or output.tell() + len(chunk) > MAX_FILE_BYTES
                    ):
                        raise CompilerServiceError(
                            "archive_limit", ARCHIVE_LIMIT, status=413
                        )
                    output.write(chunk)
        finally:
            if descriptor >= 0:
                os.close(descriptor)
