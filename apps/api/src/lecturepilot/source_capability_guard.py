"""Check captured source/publication identity under shared filesystem locks."""

from contextlib import contextmanager
import fcntl
import os
import stat

from lecturepilot.course_update_storage import course_update_lock_held
from lecturepilot.workspace_fs import WorkspaceFSError


@contextmanager
def shared_source_access(course_root, published_dir):
    paths = []
    if not course_update_lock_held(course_root):
        paths.append(course_root.parent / ".course-locks" / f"{course_root.name}.lock")
    paths.append(published_dir.parent / f".{published_dir.name}.lock")
    descriptors = []
    try:
        for path in paths:
            descriptor = os.open(path, os.O_RDWR | getattr(os, "O_NOFOLLOW", 0))
            descriptors.append(descriptor)
            info = os.fstat(descriptor)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise WorkspaceFSError("Invalid source access lock.")
            fcntl.flock(descriptor, fcntl.LOCK_SH)
        if any((course_root / "builder" / "updates").glob("*/.applying")):
            raise WorkspaceFSError("Source update recovery is required before reading.")
        yield
    except OSError as exc:
        raise WorkspaceFSError("Published source capability is unavailable or stale.") from exc
    finally:
        for descriptor in reversed(descriptors):
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)


def source_state_identity(layout, course_id, lecture_id):
    published = layout.course_canvas_dir(course_id, lecture_id)
    paths = [
        layout.course_root(course_id) / "builder" / "course-workspace.json",
        layout.course_source_index_path(course_id),
        layout.course_source_routing_path(course_id),
        layout.lecture_source_manifest_path(course_id, lecture_id),
        published,
        *sorted(published.rglob("*.json")),
        *sorted(published.rglob("*.md")),
    ]
    result = []
    for path in paths:
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode):
            raise WorkspaceFSError("Source identity cannot contain symbolic links.")
        result.append((str(path), info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns))
    return tuple(result)
