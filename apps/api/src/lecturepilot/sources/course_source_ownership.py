from __future__ import annotations

from collections.abc import Collection


_DERIVED_SOURCE_REF_PREFIXES = (
    "pages ",
    "slide ",
    "sheet ",
    "frame ",
    "frames ",
    "compiled preview",
)


def routed_source_owner(source_ref: str | None, routed_paths: Collection[str]) -> str | None:
    if source_ref is None:
        return None
    candidates = [
        path
        for path in routed_paths
        if source_ref == path or _is_derived_source_ref(source_ref, path)
    ]
    return max(candidates, key=len, default=None)


def _is_derived_source_ref(source_ref: str, path: str) -> bool:
    if source_ref.startswith(f"{path}#"):
        return True
    prefix = f"{path} "
    if not source_ref.startswith(prefix):
        return False
    suffix = source_ref[len(prefix) :]
    return suffix.startswith(_DERIVED_SOURCE_REF_PREFIXES)
