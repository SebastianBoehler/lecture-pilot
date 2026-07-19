from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
import re


_SOURCE_SUFFIXES = {".cls", ".sty", ".tex"}
_GRAPHIC_EXTENSIONS = {".jpeg", ".jpg", ".pdf", ".png"}
_REFERENCE_RE = re.compile(
    r"\\(?P<command>includegraphics|includepdf|lstinputlisting|RequirePackage|"
    r"usepackage|subfile|include|input|igh|ig)"
    r"(?:<[^>]*>)?(?:\[[^]]*])?\s*\{(?P<path>[^{}]+)}"
)
_GRAPHICS_PATH_RE = re.compile(r"\\graphicspath\s*\{(?P<paths>(?:\{[^{}]*})+)}")
_GRAPHICS_PATH_ENTRY_RE = re.compile(r"\{(?P<path>[^{}]*)}")


def prepare_source_tree(source_root: Path, main: Path) -> None:
    """Add safe aliases for common cross-platform course-source layouts."""
    for requested, actual in _planned_case_aliases(source_root):
        _link_file_alias(source_root, requested, actual)
    _add_root_search_aliases(source_root, main.parent)


def _planned_case_aliases(
    source_root: Path,
) -> list[tuple[PurePosixPath, PurePosixPath]]:
    files = sorted(
        path.relative_to(source_root)
        for path in source_root.rglob("*")
        if path.is_file() and not path.is_symlink()
    )
    sources = [path for path in files if path.suffix.lower() in _SOURCE_SUFFIXES]
    content = {
        path: (source_root / path).read_text(encoding="utf-8", errors="replace")
        for path in sources
    }
    graphics_paths = tuple(
        dict.fromkeys(
            path for text in content.values() for path in _read_graphics_paths(text)
        )
    )
    aliases: dict[str, tuple[PurePosixPath, PurePosixPath]] = {}
    for source, text in content.items():
        for match in _REFERENCE_RE.finditer(text):
            command = match.group("command")
            values = (
                match.group("path").split(",")
                if "ackage" in command
                else [match.group("path")]
            )
            for value in values:
                reference = _safe_reference(value)
                if reference is None:
                    continue
                search_paths = (
                    graphics_paths
                    if command in {"ig", "igh", "includegraphics"}
                    else ()
                )
                for requested in _reference_candidates(
                    source.parent, reference, search_paths
                ):
                    actual = _casefold_match(files, requested, command)
                    if actual is None:
                        continue
                    alias = (
                        requested
                        if requested.suffix
                        else requested.with_suffix(actual.suffix.lower())
                    )
                    if alias != actual:
                        aliases.setdefault(alias.as_posix(), (alias, actual))
    return list(aliases.values())


def _read_graphics_paths(source: str) -> list[PurePosixPath]:
    paths = []
    for match in _GRAPHICS_PATH_RE.finditer(source):
        for entry in _GRAPHICS_PATH_ENTRY_RE.finditer(match.group("paths")):
            if path := _safe_reference(entry.group("path")):
                paths.append(path)
    return paths


def _reference_candidates(
    parent: PurePosixPath,
    reference: PurePosixPath,
    search_paths: tuple[PurePosixPath, ...],
) -> list[PurePosixPath]:
    bases = (parent, PurePosixPath("."))
    candidates = [base / reference for base in bases]
    candidates.extend(
        base / search / reference for search in search_paths for base in bases
    )
    return list(dict.fromkeys(_normalized(path) for path in candidates))


def _casefold_match(
    files: list[PurePosixPath], requested: PurePosixPath, command: str
) -> PurePosixPath | None:
    allowed = _allowed_extensions(command)
    requested_key = requested.as_posix().casefold()
    for actual in files:
        if allowed and actual.suffix.lower() not in allowed:
            continue
        actual_key = actual.as_posix().casefold()
        if actual_key == requested_key:
            return actual
        if (
            not requested.suffix
            and actual.with_suffix("").as_posix().casefold() == requested_key
        ):
            return actual
    return None


def _allowed_extensions(command: str) -> set[str]:
    if command in {"input", "include", "subfile"}:
        return {".tex"}
    if "ackage" in command:
        return {".sty"}
    if command == "includepdf":
        return {".pdf"}
    if command in {"ig", "igh", "includegraphics"}:
        return _GRAPHIC_EXTENSIONS
    return set()


def _safe_reference(value: str) -> PurePosixPath | None:
    value = value.strip()
    if not value or any(character in value for character in "\\#$%{}~:"):
        return None
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        return None
    normalized = _normalized(path)
    return normalized if normalized.parts else None


def _normalized(path: PurePosixPath) -> PurePosixPath:
    return PurePosixPath(*(part for part in path.parts if part not in {"", "."}))


def _link_file_alias(
    root: Path, requested: PurePosixPath, actual: PurePosixPath
) -> None:
    actual_path = root.joinpath(*actual.parts).resolve(strict=True)
    requested_path = root.joinpath(*requested.parts)
    _ensure_directory_aliases(root, requested.parent, actual.parent)
    if _has_exact_child(requested_path.parent, requested_path.name):
        return
    try:
        os.link(actual_path, requested_path)
    except FileExistsError:
        pass  # The host filesystem is already case-insensitive.


def _ensure_directory_aliases(
    root: Path, requested: PurePosixPath, actual: PurePosixPath
) -> None:
    requested_parent = root
    actual_parent = root
    for requested_part, actual_part in zip(requested.parts, actual.parts, strict=True):
        requested_parent /= requested_part
        actual_parent /= actual_part
        if requested_part == actual_part or _has_exact_child(
            requested_parent.parent, requested_part
        ):
            continue
        try:
            requested_parent.symlink_to(
                os.path.relpath(actual_parent, requested_parent.parent),
                target_is_directory=True,
            )
        except FileExistsError:
            pass


def _add_root_search_aliases(source_root: Path, main_parent: Path) -> None:
    if main_parent == source_root:
        return
    main_top_level = main_parent.relative_to(source_root).parts[0]
    for entry in list(source_root.iterdir()):
        if entry.name == main_top_level or _has_exact_child(main_parent, entry.name):
            continue
        alias = main_parent / entry.name
        if entry.is_dir():
            alias.symlink_to(
                os.path.relpath(entry, main_parent), target_is_directory=True
            )
        else:
            os.link(entry, alias)


def _has_exact_child(parent: Path, name: str) -> bool:
    return parent.is_dir() and any(child.name == name for child in parent.iterdir())
