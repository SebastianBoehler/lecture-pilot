from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from hashlib import sha256
import errno
import os
from pathlib import Path, PurePosixPath
import stat
import unicodedata

from lecturepilot.agent_tool_utils import ToolPath, normalize_logical_path
from lecturepilot.workspace_capability import CapabilityRoot, WorkspaceCapability


class WorkspaceFSError(ValueError):
    pass


class WorkspaceFS:
    """Capability-scoped filesystem access with no-follow local file opens."""

    def __init__(self, capability: WorkspaceCapability) -> None:
        self.capability = capability
        self._guarded = ContextVar("workspace_read_guards", default=frozenset())

    @contextmanager
    def operation(self, logical_path):
        if logical_path == "/":
            yield
            return
        _, root, _ = self._select(logical_path, for_write=False)
        with self._read_guard(root):
            yield

    @contextmanager
    def _read_guard(self, root):
        if root.read_guard is None or id(root) in self._guarded.get():
            yield
            return
        with root.read_guard():
            token = self._guarded.set(self._guarded.get() | {id(root)})
            try:
                yield
            finally:
                self._guarded.reset(token)

    def logical_roots(self) -> list[str]:
        return self.capability.logical_roots()

    def resolve(self, logical_path: str, *, for_write: bool = False) -> ToolPath:
        normalized, root, relative = self._select(logical_path, for_write=for_write)
        with self._read_guard(root):
            self._verify_components(root, relative, allow_missing=for_write)
        return ToolPath(normalized, root.host_path.joinpath(*relative.parts))

    def logical_for(self, path: Path, *, allow_missing: bool = False) -> str:
        absolute = path.absolute()
        roots = sorted(
            self.capability.roots, key=lambda root: len(root.host_path.parts), reverse=True
        )
        for root in roots:
            try:
                relative = absolute.relative_to(root.host_path.absolute())
            except ValueError:
                continue
            self._verify_components(
                root, PurePosixPath(relative.as_posix()), allow_missing=allow_missing
            )
            suffix = relative.as_posix()
            logical = f"{root.logical_path}/{suffix}".rstrip("/")
            self._select(logical, for_write=False)
            return logical
        raise WorkspaceFSError("Host path is outside the workspace capability.")

    def read_text(self, logical_path: str, *, errors: str = "strict") -> str:
        _, root, relative = self._select(logical_path, for_write=False)
        with self._read_guard(root):
            fd = self._open_file(root, relative, os.O_RDONLY)
            with os.fdopen(fd, "rb") as handle:
                content = handle.read()
            if root.file_digests is not None:
                expected = dict(root.file_digests).get(relative.as_posix())
                if expected is None or sha256(content).hexdigest() != expected:
                    raise WorkspaceFSError(
                        "Workspace source no longer matches its publication digest."
                    )
            return content.decode("utf-8", errors=errors)

    def write_text(self, logical_path: str, content: str) -> None:
        _, root, relative = self._select(logical_path, for_write=True)
        parent_fd, name = self._open_parent(root, relative, create=True)
        flags = os.O_WRONLY | os.O_CREAT | _no_follow()
        try:
            fd = os.open(name, flags, 0o600, dir_fd=parent_fd)
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                os.close(fd)
                raise WorkspaceFSError("Workspace writes require a single-link regular file.")
            os.ftruncate(fd, 0)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(content)
        except OSError as exc:
            raise _safe_os_error(exc) from exc
        finally:
            os.close(parent_fd)

    def files(self, logical_path: str) -> list[ToolPath]:
        resolved = self.resolve(logical_path)
        if not resolved.path.exists():
            return []
        if resolved.path.is_file():
            return [resolved]
        files: list[ToolPath] = []
        for directory, names, filenames in os.walk(resolved.path, followlinks=False):
            directory_path = Path(directory)
            names[:] = [
                name
                for name in names
                if not name.startswith(".")
                and self.is_visible(
                    f"{resolved.logical}/{(directory_path / name).relative_to(resolved.path).as_posix()}"
                )
            ]
            for name in names:
                self._assert_not_symlink(directory_path / name)
            for name in filenames:
                if name.startswith("."):
                    continue
                path = directory_path / name
                logical = f"{resolved.logical}/{path.relative_to(resolved.path).as_posix()}"
                if not self.is_visible(logical):
                    continue
                self._assert_regular_single_link(path)
                logical = self.logical_for(path)
                self.resolve(logical)
                files.append(ToolPath(logical, path))
        return files

    def is_visible(self, logical_path: str) -> bool:
        try:
            self._select(logical_path, for_write=False)
        except WorkspaceFSError:
            return False
        return True

    def _select(
        self, logical_path: str, *, for_write: bool
    ) -> tuple[str, CapabilityRoot, PurePosixPath]:
        if unicodedata.normalize("NFC", logical_path) != logical_path:
            raise WorkspaceFSError("Workspace paths must use normalized Unicode.")
        try:
            normalized = normalize_logical_path(logical_path)
        except ValueError as exc:
            raise WorkspaceFSError(str(exc)) from exc
        roots = sorted(self.capability.roots, key=lambda root: len(root.logical_path), reverse=True)
        for root in roots:
            if normalized != root.logical_path and not normalized.startswith(
                f"{root.logical_path}/"
            ):
                continue
            if for_write and not root.writable:
                raise WorkspaceFSError("This workspace root is read-only.")
            suffix = normalized.removeprefix(root.logical_path).lstrip("/")
            if any(
                part.casefold() in {name.casefold() for name in root.excluded_names}
                for part in PurePosixPath(suffix).parts
            ):
                raise WorkspaceFSError("Path is outside the workspace capability.")
            if (
                root.allowed_files is not None
                and suffix
                and not any(
                    path == suffix or path.startswith(f"{suffix}/") for path in root.allowed_files
                )
            ):
                raise WorkspaceFSError("Path is outside the workspace capability.")
            return normalized, root, PurePosixPath(suffix)
        raise WorkspaceFSError("Path is outside the workspace capability.")

    def _verify_components(
        self, root: CapabilityRoot, relative: PurePosixPath, *, allow_missing: bool
    ) -> None:
        self._assert_not_symlink(root.host_path)
        current = root.host_path
        for part in relative.parts:
            current /= part
            try:
                self._assert_not_symlink(current)
            except FileNotFoundError:
                if allow_missing:
                    return
                raise WorkspaceFSError("Workspace path does not exist.") from None

    def _open_file(self, root: CapabilityRoot, relative: PurePosixPath, flags: int) -> int:
        parent_fd, name = self._open_parent(root, relative, create=False)
        try:
            fd = os.open(name, flags | _no_follow(), dir_fd=parent_fd)
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                os.close(fd)
                raise WorkspaceFSError("Workspace reads require a single-link regular file.")
            return fd
        except OSError as exc:
            raise _safe_os_error(exc) from exc
        finally:
            os.close(parent_fd)

    def _open_parent(
        self, root: CapabilityRoot, relative: PurePosixPath, *, create: bool
    ) -> tuple[int, str]:
        if not relative.parts:
            raise WorkspaceFSError("A file path is required.")
        flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | _no_follow()
        try:
            fd = os.open(root.host_path, flags)
            for part in relative.parts[:-1]:
                try:
                    child = os.open(part, flags, dir_fd=fd)
                except FileNotFoundError:
                    if not create:
                        raise
                    os.mkdir(part, 0o700, dir_fd=fd)
                    child = os.open(part, flags, dir_fd=fd)
                os.close(fd)
                fd = child
            return fd, relative.parts[-1]
        except OSError as exc:
            raise _safe_os_error(exc) from exc

    @staticmethod
    def _assert_not_symlink(path: Path) -> None:
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode):
            raise WorkspaceFSError("Symbolic links are not allowed in workspace roots.")

    @staticmethod
    def _assert_regular_single_link(path: Path) -> None:
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode):
            raise WorkspaceFSError("Symbolic links are not allowed in workspace roots.")
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise WorkspaceFSError("Workspace reads require a single-link regular file.")


def _no_follow() -> int:
    return getattr(os, "O_NOFOLLOW", 0)


def _safe_os_error(exc: OSError) -> WorkspaceFSError:
    if exc.errno in {errno.ELOOP, errno.ENOTDIR}:
        return WorkspaceFSError("Symbolic links are not allowed in workspace roots.")
    if exc.errno == errno.ENOENT:
        return WorkspaceFSError("Workspace path does not exist.")
    return WorkspaceFSError("Workspace file operation failed.")
