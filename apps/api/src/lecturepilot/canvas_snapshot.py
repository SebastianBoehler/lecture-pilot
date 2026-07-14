from __future__ import annotations

import fcntl
import os
import shutil
import tempfile
from contextlib import ExitStack, contextmanager
from pathlib import Path
from threading import Lock, RLock
from typing import Callable, Iterator, TypeVar
from uuid import uuid4


_T = TypeVar("_T")
_LOCK_REGISTRY_GUARD = Lock()
_LOCK_REGISTRY: dict[Path, RLock] = {}


@contextmanager
def locked_canvas_paths(*paths: Path) -> Iterator[None]:
    """Serialize canvas access across threads and API worker processes."""

    resolved = sorted({path.resolve() for path in paths}, key=str)
    with ExitStack() as stack:
        for path in resolved:
            stack.enter_context(_thread_lock(path))
        for path in resolved:
            stack.enter_context(_file_lock(path))
        for path in resolved:
            _recover_interrupted_replace(path)
        yield


def replace_canvas_snapshot(target: Path, build_validated: Callable[[Path], _T]) -> _T:
    """Build a complete snapshot before replacing the current directory."""

    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{target.name}.staging-", dir=target.parent))
    previous: Path | None = None
    try:
        result = build_validated(staging)
        _fsync_tree(staging)
        if target.exists():
            previous = target.parent / f".{target.name}.previous-{uuid4().hex}"
        try:
            if previous is not None:
                os.replace(target, previous)
                _fsync_directory(target.parent)
            os.replace(staging, target)
            _fsync_directory(target.parent)
        except BaseException:
            if previous is not None and previous.exists():
                if target.exists():
                    shutil.rmtree(target)
                os.replace(previous, target)
                _fsync_directory(target.parent)
                previous = None
            raise
        if previous is not None:
            shutil.rmtree(previous, ignore_errors=True)
        return result
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)


@contextmanager
def _thread_lock(path: Path) -> Iterator[None]:
    with _LOCK_REGISTRY_GUARD:
        lock = _LOCK_REGISTRY.setdefault(path, RLock())
    with lock:
        yield


@contextmanager
def _file_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.parent / f".{path.name}.lock"
    with lock_path.open("a+b") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _recover_interrupted_replace(target: Path) -> None:
    previous = sorted(
        target.parent.glob(f".{target.name}.previous-*"),
        key=lambda path: path.stat().st_mtime_ns,
        reverse=True,
    )
    if not target.exists() and previous:
        os.replace(previous.pop(0), target)
        _fsync_directory(target.parent)
    if target.exists():
        for path in previous:
            shutil.rmtree(path, ignore_errors=True)
    for path in target.parent.glob(f".{target.name}.staging-*"):
        shutil.rmtree(path, ignore_errors=True)


def _fsync_tree(root: Path) -> None:
    directories = [root]
    for path in root.rglob("*"):
        if path.is_symlink():
            continue
        if path.is_dir():
            directories.append(path)
        elif path.is_file():
            with path.open("rb") as file:
                os.fsync(file.fileno())
    for directory in reversed(directories):
        _fsync_directory(directory)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
