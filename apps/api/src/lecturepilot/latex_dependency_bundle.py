from __future__ import annotations

from collections import deque
from pathlib import Path, PurePosixPath
import re

from lecturepilot.latex_canvas_assets import read_graphicspaths
from lecturepilot.latex_macro_assets import expanded_macro_asset_references
from lecturepilot.source_index_models import CourseSourceIndex, IndexedSourceFile


_TEXT_KINDS = {"latex", "latex-support"}
_TEX_EXTENSIONS = (".tex", ".sty", ".cls")
_ASSET_EXTENSIONS = (".pdf", ".png", ".jpg", ".jpeg", ".svg")
_MAX_TEX_BYTES = 10 * 1024 * 1024


def resolve_latex_compiler_inputs(
    *,
    source_root: Path,
    source_index: CourseSourceIndex,
    source_path: str,
    forbidden_paths: set[str] | None = None,
) -> list[IndexedSourceFile]:
    """Return only local files reachable from one scheduled TeX document."""
    indexed = {item.path.casefold(): item for item in source_index.files}
    main = indexed.get(source_path.casefold())
    if main is None or main.kind != "latex":
        return []

    forbidden = {path.casefold() for path in forbidden_paths or set()}
    included: dict[str, IndexedSourceFile] = {}
    sources: dict[str, str] = {}
    queue = deque([main])
    while queue:
        item = queue.popleft()
        key = item.path.casefold()
        if key in included or (key in forbidden and item.path != main.path):
            continue
        included[key] = item
        if item.kind not in _TEXT_KINDS:
            continue
        source = _read_tex(source_root, item)
        sources[item.path] = source
        parent = PurePosixPath(item.path).parent
        for reference, extensions in _tex_dependencies(source):
            dependency = _resolve(indexed, parent, reference, extensions)
            if dependency is not None:
                queue.append(dependency)

    graphicspaths = tuple(
        dict.fromkeys(path for source in sources.values() for path in read_graphicspaths(source))
    )
    for path, source in sources.items():
        parent = PurePosixPath(path).parent
        for reference in _asset_references(source):
            dependency = _resolve(
                indexed,
                parent,
                reference,
                _ASSET_EXTENSIONS,
                search_paths=graphicspaths,
            )
            if dependency is not None and dependency.path.casefold() not in forbidden:
                included[dependency.path.casefold()] = dependency
        for reference in _listing_references(source):
            dependency = _resolve(indexed, parent, reference, ())
            if dependency is not None and dependency.path.casefold() not in forbidden:
                included[dependency.path.casefold()] = dependency
    main_parent = PurePosixPath(main.path).parent
    for reference in expanded_macro_asset_references(list(sources.values())):
        dependency = _resolve(
            indexed,
            main_parent,
            reference,
            _ASSET_EXTENSIONS,
            search_paths=graphicspaths,
        )
        if dependency is not None and dependency.path.casefold() not in forbidden:
            included[dependency.path.casefold()] = dependency
    return sorted(included.values(), key=lambda item: item.path.casefold())


def _read_tex(source_root: Path, item: IndexedSourceFile) -> str:
    if item.size_bytes > _MAX_TEX_BYTES:
        return ""
    root = source_root.resolve(strict=True)
    path = (source_root / item.path).resolve(strict=True)
    if not path.is_relative_to(root) or not path.is_file() or path.is_symlink():
        return ""
    return _strip_comments(path.read_text(encoding="utf-8", errors="replace"))


def _tex_dependencies(source: str) -> list[tuple[str, tuple[str, ...]]]:
    dependencies: list[tuple[str, tuple[str, ...]]] = []
    for match in _INPUT_RE.finditer(source):
        dependencies.append((match.group("path"), _TEX_EXTENSIONS))
    for match in _PACKAGE_RE.finditer(source):
        dependencies.extend((name.strip(), (".sty",)) for name in match.group("names").split(","))
    for match in _CLASS_RE.finditer(source):
        dependencies.append((match.group("name").strip(), (".cls",)))
    for match in _BIBLIOGRAPHY_RE.finditer(source):
        dependencies.extend((name.strip(), (".bib",)) for name in match.group("names").split(","))
    for match in _BIBLIOGRAPHY_STYLE_RE.finditer(source):
        dependencies.append((match.group("name").strip(), (".bst",)))
    for match in _THEME_RE.finditer(source):
        prefix = _THEME_PREFIXES[match.group("kind") or ""]
        dependencies.append((f"{prefix}{match.group('name').strip()}", (".sty",)))
    return dependencies


def _asset_references(source: str) -> list[str]:
    references = [match.group("path") for match in _ASSET_RE.finditer(source)]
    references.extend(match.group("path") for match in _INCLUDE_PDF_RE.finditer(source))
    return references


def _listing_references(source: str) -> list[str]:
    return [match.group("path") for match in _LISTING_RE.finditer(source)]


def _resolve(
    indexed: dict[str, IndexedSourceFile],
    parent: PurePosixPath,
    raw_reference: str,
    extensions: tuple[str, ...],
    *,
    search_paths: tuple[PurePosixPath, ...] = (),
) -> IndexedSourceFile | None:
    reference = _safe_reference(raw_reference)
    if reference is None:
        return None
    bases = (parent, PurePosixPath("."))
    candidates = [base / reference for base in bases]
    candidates.extend(base / search / reference for search in search_paths for base in bases)
    for candidate in dict.fromkeys(_normalized(path) for path in candidates):
        variants = (
            (candidate,)
            if candidate.suffix
            else tuple(candidate.with_suffix(extension) for extension in extensions)
        )
        for variant in variants:
            if item := indexed.get(variant.as_posix().casefold()):
                return item
    return None


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


def _strip_comments(source: str) -> str:
    lines = []
    for line in source.splitlines():
        position = next(
            (
                index
                for index, character in enumerate(line)
                if character == "%" and (index == 0 or line[index - 1] != "\\")
            ),
            len(line),
        )
        lines.append(line[:position])
    return "\n".join(lines)


_INPUT_RE = re.compile(r"\\(?:input|include|subfile)\s*\{(?P<path>[^{}]+)}")
_PACKAGE_RE = re.compile(r"\\usepackage(?:\[[^]]*])?\s*\{(?P<names>[^{}]+)}")
_CLASS_RE = re.compile(
    r"\\(?:documentclass|LoadClass|LoadClassWithOptions)(?:\[[^]]*])?"
    r"\s*\{(?P<name>[^{}]+)}"
)
_BIBLIOGRAPHY_RE = re.compile(r"\\bibliography\s*\{(?P<names>[^{}]+)}")
_BIBLIOGRAPHY_STYLE_RE = re.compile(r"\\bibliographystyle\s*\{(?P<name>[^{}]+)}")
_THEME_RE = re.compile(
    r"\\use(?P<kind>color|font|inner|outer)?theme(?:\[[^]]*])?\s*\{(?P<name>[^{}]+)}"
)
_THEME_PREFIXES = {
    "": "beamertheme",
    "color": "beamercolortheme",
    "font": "beamerfonttheme",
    "inner": "beamerinnertheme",
    "outer": "beameroutertheme",
}
_ASSET_RE = re.compile(
    r"\\(?:includegraphics|ig|igh)(?:<[^>]*>)?(?:\[[^]]*])?\s*\{(?P<path>[^{}]+)}"
)
_INCLUDE_PDF_RE = re.compile(r"\\includepdf(?:\[[^]]*])?\s*\{(?P<path>[^{}]+)}")
_LISTING_RE = re.compile(r"\\lstinputlisting(?:\[[^]]*])?\s*\{(?P<path>[^{}]+)}")
