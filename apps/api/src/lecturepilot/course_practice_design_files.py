from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from hashlib import sha256
import fcntl
import os
from pathlib import Path
from typing import Protocol

from lecturepilot.durable_files import atomic_write_text, ensure_durable_directory, fsync_directory


class _JsonModel(Protocol):
    def model_dump_json(self, *, indent: int) -> str: ...


@contextmanager
def locked_design_file(path: Path) -> Iterator[None]:
    ensure_durable_directory(path.parent)
    descriptor = os.open(path.parent / ".practice-design.lock", os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def write_design_file(path: Path, design: _JsonModel) -> None:
    if path.exists():
        previous = path.read_bytes()
        history = path.parent / path.stem / "history"
        ensure_durable_directory(history)
        snapshot = history / f"{sha256(previous).hexdigest()}.json"
        if not snapshot.exists():
            with snapshot.open("xb") as handle:
                os.chmod(snapshot, 0o600)
                handle.write(previous)
                handle.flush()
                os.fsync(handle.fileno())
            fsync_directory(history)
    atomic_write_text(path, design.model_dump_json(indent=2))
