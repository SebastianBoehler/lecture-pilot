from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import stat
import tempfile

from lecturepilot.workspace_fs import WorkspaceFSError


def atomic_copy(source: Path, target: Path) -> None:
    assert_single_link_regular(source)
    ensure_durable_directory(target.parent)
    descriptor, temporary = tempfile.mkstemp(prefix=".course-update-", dir=target.parent)
    temporary_path = Path(temporary)
    try:
        source_fd = os.open(source, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            info = os.fstat(source_fd)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise WorkspaceFSError("Course updates require single-link regular files.")
            with (
                os.fdopen(source_fd, "rb", closefd=False) as reader,
                os.fdopen(descriptor, "wb") as writer,
            ):
                shutil.copyfileobj(reader, writer, length=1024 * 1024)
                writer.flush()
                os.fsync(writer.fileno())
        finally:
            os.close(source_fd)
        os.chmod(temporary_path, 0o600)
        temporary_path.replace(target)
        fsync_directory(target.parent)
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
        temporary_path.unlink(missing_ok=True)
        raise


def atomic_write_json(path: Path, value: object) -> None:
    ensure_durable_directory(path.parent)
    descriptor, temporary = tempfile.mkstemp(prefix=".course-update-recovery-", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_path, 0o600)
        temporary_path.replace(path)
        fsync_directory(path.parent)
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
        temporary_path.unlink(missing_ok=True)
        raise


def assert_single_link_regular(path: Path) -> None:
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise WorkspaceFSError("Course updates require single-link regular files.")


def ensure_durable_directory(path: Path, *, mode: int = 0o700) -> None:
    missing: list[Path] = []
    cursor = path
    while not cursor.exists() and cursor.parent != cursor:
        missing.append(cursor)
        cursor = cursor.parent
    path.mkdir(parents=True, mode=mode, exist_ok=True)
    for directory in reversed(missing):
        fsync_directory(directory)
        fsync_directory(directory.parent)


def fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
