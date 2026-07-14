from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
import logging
import os
from pathlib import Path
import shutil
import stat
from threading import local, Lock, RLock
from uuid import uuid4

from lecturepilot.durable_files import (
    atomic_copy as _atomic_copy,
    atomic_write_json as _atomic_write_json,
    assert_single_link_regular as _assert_regular,
    ensure_durable_directory,
    fsync_directory,
)
from lecturepilot.workspace_capability import CapabilityRoot, WorkspaceCapability
from lecturepilot.workspace_fs import WorkspaceFS, WorkspaceFSError


logger = logging.getLogger(__name__)
_LOCKS_GUARD = Lock()
_COURSE_LOCKS: dict[str, RLock] = {}
_LOCK_DEPTH = local()


class CourseUpdateRecoveryError(RuntimeError):
    """Raised when an update cannot be rolled back automatically."""

    def __init__(self, recovery_id: str) -> None:
        self.recovery_id = recovery_id
        super().__init__(f"Course update recovery required (recovery id: {recovery_id}).")


@contextmanager
def course_update_lock(course_root: Path) -> Iterator[None]:
    """Serialize course mutations across threads and API worker processes."""

    key = str(course_root.resolve())
    with _LOCKS_GUARD:
        local_lock = _COURSE_LOCKS.setdefault(key, RLock())
    with local_lock:
        depths = getattr(_LOCK_DEPTH, "courses", None)
        if depths is None:
            depths = {}
            _LOCK_DEPTH.courses = depths
        if depths.get(key, 0):
            depths[key] += 1
            try:
                yield
            finally:
                depths[key] -= 1
            return
        lock_dir = course_root.parent / ".course-locks"
        lock_dir.mkdir(parents=True, mode=0o700, exist_ok=True)
        lock_path = lock_dir / f"{course_root.name}.lock"
        flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(lock_path, flags, 0o600)
        try:
            info = os.fstat(descriptor)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise WorkspaceFSError("Course update lock must be a single-link regular file.")
            os.fchmod(descriptor, 0o600)
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            depths[key] = 1
            try:
                yield
            finally:
                depths.pop(key, None)
                fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


def course_update_lock_held(course_root: Path) -> bool:
    depths = getattr(_LOCK_DEPTH, "courses", {})
    return bool(depths.get(str(course_root.resolve()), 0))


def retire_recovery_artifact(source: Path, *, retired_root: Path) -> Path | None:
    """Atomically remove completed recovery data from the retry namespace."""

    if not source.exists():
        return None
    ensure_durable_directory(retired_root)
    retired = retired_root / f"{source.name}-{uuid4()}"
    os.rename(source, retired)
    fsync_directory(source.parent)
    fsync_directory(retired_root)
    return retired


def cleanup_retired_recovery_artifact(retired: Path | None) -> None:
    if retired is None:
        return
    try:
        shutil.rmtree(retired)
        fsync_directory(retired.parent)
    except OSError:
        logger.warning(
            "Could not remove retired recovery artifact; path=%s", retired, exc_info=True
        )
        return
    try:
        retired.parent.rmdir()
        fsync_directory(retired.parent.parent)
    except OSError:
        pass


@contextmanager
def staged_file_transaction(
    *,
    staged_root: Path,
    live_root: Path,
    backup_root: Path,
    paths: list[str],
    cleanup_on_success: bool = True,
) -> Iterator[_StagedFileTransaction]:
    recovery_id = str(uuid4())
    transaction = _StagedFileTransaction(
        staged_root,
        live_root,
        backup_root / recovery_id,
        paths,
        recovery_id=recovery_id,
    )
    transaction.apply()
    try:
        yield transaction
    except BaseException as operation_error:
        try:
            transaction.rollback()
        except CourseUpdateRecoveryError as recovery_error:
            raise recovery_error from operation_error
        transaction.cleanup()
        raise
    else:
        if cleanup_on_success:
            transaction.cleanup()


@dataclass(frozen=True)
class _TrackedFile:
    target: Path
    saved: Path | None
    logical_path: str


class _StagedFileTransaction:
    def __init__(
        self,
        staged_root: Path,
        live_root: Path,
        backup_root: Path,
        paths: list[str],
        *,
        recovery_id: str,
    ) -> None:
        self.staged_root = staged_root
        self.live_root = live_root
        self.backup_root = backup_root
        self.paths = sorted(set(paths))
        self.recovery_id = recovery_id
        self.applied: list[_TrackedFile] = []

    def apply(self) -> None:
        ensure_durable_directory(self.live_root)
        ensure_durable_directory(self.backup_root)
        staged = _workspace("/staged", self.staged_root, writable=False)
        live = _workspace("/live", self.live_root, writable=True)
        prepared: list[tuple[Path, Path]] = []
        try:
            for path in self.paths:
                source = staged.resolve(f"/staged/{path}").path
                target = _writable_target(live, f"/live/{path}")
                saved = self._save(target, f"source/{path}")
                self.applied.append(_TrackedFile(target, saved, f"source/{path}"))
                prepared.append((source, target))
            self.checkpoint()
            for source, target in prepared:
                _atomic_copy(source, target)
        except BaseException as operation_error:
            try:
                self.rollback()
            except CourseUpdateRecoveryError as recovery_error:
                raise recovery_error from operation_error
            self.cleanup()
            raise

    def track_file(self, target: Path, logical_path: str) -> None:
        if any(item.target == target for item in self.applied):
            raise ValueError("A transaction target cannot be tracked twice.")
        saved = self._save(target, f"metadata/{logical_path}")
        self.applied.append(_TrackedFile(target, saved, f"metadata/{logical_path}"))

    def checkpoint(self) -> None:
        self._write_recovery_marker(status="in_progress", failures=[])

    def rollback(self) -> None:
        failures: list[tuple[_TrackedFile, BaseException]] = []
        for item in reversed(self.applied):
            try:
                if item.saved and item.saved.exists():
                    item.target.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
                    _atomic_copy(item.saved, item.target)
                elif item.target.exists():
                    item.target.unlink()
                    fsync_directory(item.target.parent)
            except BaseException as exc:
                failures.append((item, exc))
        if failures:
            try:
                self._write_recovery_marker(status="rollback_failed", failures=failures)
            except BaseException:
                logger.exception(
                    "Could not update course recovery marker; recovery_id=%s",
                    self.recovery_id,
                )
            logger.error(
                "Course update rollback failed; recovery_id=%s failures=%d",
                self.recovery_id,
                len(failures),
            )
            raise CourseUpdateRecoveryError(self.recovery_id) from failures[0][1]
        self.applied.clear()

    def cleanup(self) -> None:
        try:
            retired = retire_recovery_artifact(
                self.backup_root,
                retired_root=self.backup_root.parent.parent / ".retired-recovery",
            )
        except Exception as exc:
            logger.exception("Could not retire course recovery artifact; id=%s", self.recovery_id)
            raise CourseUpdateRecoveryError(self.recovery_id) from exc
        try:
            self.backup_root.parent.rmdir()
            fsync_directory(self.backup_root.parent.parent)
        except OSError:
            pass
        cleanup_retired_recovery_artifact(retired)

    def _save(self, target: Path, logical_path: str) -> Path | None:
        if not target.exists():
            return None
        _assert_regular(target)
        backup = _workspace("/backup", self.backup_root, writable=True)
        saved = _writable_target(backup, f"/backup/{logical_path}")
        _atomic_copy(target, saved)
        return saved

    def _write_recovery_marker(
        self,
        *,
        status: str,
        failures: list[tuple[_TrackedFile, BaseException]],
    ) -> None:
        failed_paths = {item.logical_path for item, _ in failures}
        marker = {
            "recovery_id": self.recovery_id,
            "status": status,
            "operations": [
                {
                    "path": item.logical_path,
                    "action": "restore" if item.saved else "delete",
                    "rollback_failed": item.logical_path in failed_paths,
                }
                for item in self.applied
            ],
        }
        _atomic_write_json(self.backup_root / "recovery.json", marker)


def _workspace(logical: str, root: Path, *, writable: bool) -> WorkspaceFS:
    return WorkspaceFS(WorkspaceCapability((CapabilityRoot(logical, root, writable=writable),)))


def _writable_target(workspace: WorkspaceFS, logical_path: str) -> Path:
    target = workspace.resolve(logical_path, for_write=True).path
    ensure_durable_directory(target.parent)
    return workspace.resolve(logical_path, for_write=True).path
