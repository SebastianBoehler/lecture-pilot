"""Remember whether a published canvas snapshot is valid, keyed by the exact files it reads.

Listing courses and lectures asks, for every published lecture, whether its snapshot is valid.
Re-validating parses every section, the learning map and the document digest under the canvas
lock, so concurrent dashboard requests queued behind each other. Published snapshots only change
by replacement, so a verdict stays correct while the directory and every file validation reads
keep the same inode, size and modification time; any change re-validates.
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable
from pathlib import Path
from threading import Lock

Signature = tuple

_MAX_ENTRIES = 2048


class PublishedSnapshotValidity:
    def __init__(self, max_entries: int = _MAX_ENTRIES) -> None:
        self._entries: OrderedDict[Path, tuple[Signature, bool | Exception]] = OrderedDict()
        self._max_entries = max_entries
        self._lock = Lock()

    def check(self, published_dir: Path, validate: Callable[[], bool]) -> bool:
        """Return `validate()`'s verdict, re-raising its error, reusing it while files are unchanged."""
        before = snapshot_signature(published_dir)
        if before is None:
            return validate()
        with self._lock:
            cached = self._entries.get(published_dir)
            if cached is not None and cached[0] == before:
                self._entries.move_to_end(published_dir)
                return _replay(cached[1])
        try:
            verdict: bool | Exception = validate()
        except Exception as exc:  # noqa: BLE001 - stored and re-raised unchanged below
            verdict = exc
        if snapshot_signature(published_dir) == before:
            with self._lock:
                self._entries[published_dir] = (before, verdict)
                self._entries.move_to_end(published_dir)
                while len(self._entries) > self._max_entries:
                    self._entries.popitem(last=False)
        return _replay(verdict)


def snapshot_signature(published_dir: Path) -> Signature | None:
    """Identity of the published directory and every file snapshot validation reads."""
    try:
        directory = published_dir.stat()
    except FileNotFoundError:
        return None
    entries = [("", directory.st_ino, directory.st_mtime_ns, 0)]
    sections = published_dir / "sections"
    candidates = [*published_dir.iterdir(), *(sections.glob("*.md") if sections.is_dir() else ())]
    if sections.is_dir():
        stat = sections.stat()
        entries.append(("sections/", stat.st_ino, stat.st_mtime_ns, 0))
    for path in candidates:
        if not path.is_file():
            continue
        try:
            stat = path.stat()
        except FileNotFoundError:
            return None
        name = path.relative_to(published_dir).as_posix()
        entries.append((name, stat.st_ino, stat.st_mtime_ns, stat.st_size))
    return tuple(sorted(entries))


def _replay(verdict: bool | Exception) -> bool:
    if isinstance(verdict, Exception):
        # Drop the previous traceback so a remembered error does not grow on every replay.
        raise verdict.with_traceback(None)
    return verdict
