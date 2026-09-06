from contextlib import contextmanager
import fcntl
import os
from pathlib import Path


@contextmanager
def exclusive_authoring_job(root: Path):
    """Reject competing workers without blocking the API event loop."""
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(root / ".worker.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("This authoring job is already running.") from exc
        yield
    finally:
        os.close(descriptor)
