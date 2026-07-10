from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, TimeoutError as FutureTimeoutError
import os
import sys
from typing import Any, Callable


class BoundedProcessingError(RuntimeError):
    pass


_executor: ProcessPoolExecutor | None = None


def run_bounded(function: Callable[..., Any], *args: Any) -> Any:
    if not _enabled():
        return function(*args)
    future = _pool().submit(function, *args)
    try:
        return future.result(timeout=_positive_env("LECTUREPILOT_PROCESSING_TIMEOUT_SECONDS", 30))
    except FutureTimeoutError as exc:
        future.cancel()
        raise BoundedProcessingError("Course material processing timed out.") from exc
    except Exception as exc:
        raise BoundedProcessingError("Course material processing failed safely.") from exc


def _pool() -> ProcessPoolExecutor:
    global _executor
    if _executor is None:
        _executor = ProcessPoolExecutor(
            max_workers=_positive_env("LECTUREPILOT_PROCESSING_WORKERS", 2),
            initializer=_apply_worker_limits,
        )
    return _executor


def _apply_worker_limits() -> None:
    try:
        import resource
    except ImportError:
        return
    memory = _positive_env("LECTUREPILOT_PROCESSING_MEMORY_BYTES", 768 * 1024 * 1024)
    cpu = _positive_env("LECTUREPILOT_PROCESSING_CPU_SECONDS", 25)
    file_size = _positive_env("LECTUREPILOT_PROCESSING_FILE_BYTES", 256 * 1024 * 1024)
    if sys.platform != "darwin":
        _set_soft_limit(resource, resource.RLIMIT_AS, memory)
    _set_soft_limit(resource, resource.RLIMIT_CPU, cpu)
    _set_soft_limit(resource, resource.RLIMIT_FSIZE, file_size)
    _set_soft_limit(resource, resource.RLIMIT_NOFILE, 64)


def _set_soft_limit(resource_module: Any, kind: int, requested: int) -> None:
    _, hard = resource_module.getrlimit(kind)
    soft = requested if hard == resource_module.RLIM_INFINITY else min(requested, hard)
    resource_module.setrlimit(kind, (soft, hard))


def _enabled() -> bool:
    configured = os.getenv("LECTUREPILOT_BOUNDED_PROCESSING", "").strip().lower()
    if configured:
        return configured in {"1", "true", "yes", "on"}
    return os.getenv("LECTUREPILOT_ENV", "").strip().lower() == "production"


def _positive_env(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, str(default))))
    except ValueError:
        return default
