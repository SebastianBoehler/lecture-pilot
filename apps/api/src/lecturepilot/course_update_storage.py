from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
import os
from pathlib import Path
import shutil
import stat
import tempfile

from lecturepilot.workspace_capability import CapabilityRoot, WorkspaceCapability
from lecturepilot.workspace_fs import WorkspaceFS, WorkspaceFSError


@contextmanager
def staged_file_transaction(
    *,
    staged_root: Path,
    live_root: Path,
    backup_root: Path,
    paths: list[str],
) -> Iterator[None]:
    transaction = _StagedFileTransaction(staged_root, live_root, backup_root, paths)
    transaction.apply()
    try:
        yield
    except BaseException:
        transaction.rollback()
        raise
    finally:
        shutil.rmtree(backup_root, ignore_errors=True)


class _StagedFileTransaction:
    def __init__(
        self,
        staged_root: Path,
        live_root: Path,
        backup_root: Path,
        paths: list[str],
    ) -> None:
        self.staged_root = staged_root
        self.live_root = live_root
        self.backup_root = backup_root
        self.paths = sorted(set(paths))
        self.applied: list[tuple[Path, Path | None]] = []

    def apply(self) -> None:
        self.live_root.mkdir(parents=True, mode=0o700, exist_ok=True)
        self.backup_root.mkdir(parents=True, mode=0o700, exist_ok=True)
        staged = _workspace("/staged", self.staged_root, writable=False)
        live = _workspace("/live", self.live_root, writable=True)
        backup = _workspace("/backup", self.backup_root, writable=True)
        try:
            for path in self.paths:
                source = staged.resolve(f"/staged/{path}").path
                target = _writable_target(live, f"/live/{path}")
                saved = None
                if target.exists():
                    _assert_regular(target)
                    saved = _writable_target(backup, f"/backup/{path}")
                    _atomic_copy(target, saved)
                _atomic_copy(source, target)
                self.applied.append((target, saved))
        except BaseException:
            self.rollback()
            shutil.rmtree(self.backup_root, ignore_errors=True)
            raise

    def rollback(self) -> None:
        for target, saved in reversed(self.applied):
            if saved and saved.exists():
                _atomic_copy(saved, target)
            else:
                target.unlink(missing_ok=True)
        self.applied.clear()


def _workspace(logical: str, root: Path, *, writable: bool) -> WorkspaceFS:
    return WorkspaceFS(WorkspaceCapability((CapabilityRoot(logical, root, writable=writable),)))


def _writable_target(workspace: WorkspaceFS, logical_path: str) -> Path:
    target = workspace.resolve(logical_path, for_write=True).path
    target.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    return workspace.resolve(logical_path, for_write=True).path


def _atomic_copy(source: Path, target: Path) -> None:
    _assert_regular(source)
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
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
        temporary_path.unlink(missing_ok=True)
        raise


def _assert_regular(path: Path) -> None:
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise WorkspaceFSError("Course updates require single-link regular files.")
