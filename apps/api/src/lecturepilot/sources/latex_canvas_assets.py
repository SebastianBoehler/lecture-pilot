from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


BROWSER_ASSET_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".svg", ".pdf"}
BROWSER_IMAGE_SUFFIXES = BROWSER_ASSET_SUFFIXES
_MAX_CANVAS_ASSET_BYTES = 20 * 1024 * 1024
_EXTENSION_ORDER = (".jpg", ".jpeg", ".png", ".webp", ".svg", ".pdf")


@dataclass(frozen=True)
class LatexAssetResolver:
    material_root: Path
    graphicspaths: tuple[PurePosixPath, ...]

    @classmethod
    def from_source(cls, source: str, *, material_root: Path) -> LatexAssetResolver:
        return cls(
            material_root=material_root,
            graphicspaths=read_graphicspaths(source),
        )

    def read_assets(self, body: str) -> list[str]:
        assets: list[str] = []
        for match in LATEX_ASSET_RE.finditer(body):
            asset = self.resolve(match.group("path").strip())
            if asset and asset not in assets:
                assets.append(asset)
        return collapse_overlay_assets(assets)

    def resolve(self, raw_path: str) -> str | None:
        include_path = _safe_relative_path(raw_path)
        if include_path is None:
            return None
        for candidate, asset_path in self._candidate_paths(include_path):
            if resolved := _resolve_candidate(candidate, self.material_root):
                return asset_path.with_suffix(resolved.suffix).as_posix()
        return None

    def _candidate_paths(
        self, include_path: PurePosixPath
    ) -> list[tuple[PurePosixPath, PurePosixPath]]:
        candidates = [(include_path, include_path)]
        candidates.extend((root / include_path, root / include_path) for root in self.graphicspaths)
        legacy_path = PurePosixPath("images") / _without_images_prefix(include_path)
        candidates.append((legacy_path, _without_images_prefix(include_path)))
        return list(dict.fromkeys(candidates))


def read_graphicspaths(source: str) -> tuple[PurePosixPath, ...]:
    matches = list(_GRAPHICSPATH_RE.finditer(source))
    if not matches:
        return ()
    roots = []
    for raw_path in _GRAPHICSPATH_ENTRY_RE.findall(matches[-1].group("entries")):
        if path := _safe_relative_path(raw_path.strip()):
            roots.append(path)
    return tuple(dict.fromkeys(roots))


def is_allowed_canvas_asset(path: Path) -> bool:
    return (
        path.exists()
        and path.is_file()
        and path.suffix.lower() in BROWSER_ASSET_SUFFIXES
        and path.stat().st_size <= _MAX_CANVAS_ASSET_BYTES
    )


def collapse_overlay_assets(assets: list[str]) -> list[str]:
    selected: dict[str, tuple[int, str]] = {}
    order: list[str] = []
    for asset in assets:
        key, number = _overlay_asset_key(asset)
        if key not in selected:
            order.append(key)
            selected[key] = (number, asset)
        elif number >= selected[key][0]:
            selected[key] = (number, asset)
    return [selected[key][1] for key in order]


def _resolve_candidate(relative: PurePosixPath, material_root: Path) -> Path | None:
    suffix = relative.suffix.lower()
    if suffix:
        return _allowed_path(material_root, relative) if suffix in BROWSER_ASSET_SUFFIXES else None
    for extension in _EXTENSION_ORDER:
        if path := _allowed_path(material_root, relative.with_suffix(extension)):
            return path
    return None


def _allowed_path(material_root: Path, relative: PurePosixPath) -> Path | None:
    root = material_root.resolve()
    candidate = (root / relative.as_posix()).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate if is_allowed_canvas_asset(candidate) else None


def _safe_relative_path(raw_path: str) -> PurePosixPath | None:
    path = PurePosixPath(raw_path)
    if not raw_path or path.is_absolute() or ".." in path.parts:
        return None
    normalized = PurePosixPath(*[part for part in path.parts if part not in {"", "."}])
    return normalized if normalized.parts else None


def _without_images_prefix(path: PurePosixPath) -> PurePosixPath:
    return PurePosixPath(*path.parts[1:]) if path.parts[:1] == ("images",) else path


def _overlay_asset_key(asset: str) -> tuple[str, int]:
    match = _OVERLAY_ASSET_RE.match(asset)
    if not match:
        return asset, 0
    return f"{match.group('base')}{match.group('suffix')}", int(match.group("number"))


LATEX_ASSET_RE = re.compile(r"\\(?:ig|includegraphics)(?:\[[^]]*])?\{(?P<path>[^{}]+)}")
_GRAPHICSPATH_RE = re.compile(
    r"\\graphicspath\s*\{(?P<entries>(?:\s*\{[^{}]*}\s*)+)}",
    re.DOTALL,
)
_GRAPHICSPATH_ENTRY_RE = re.compile(r"\{([^{}]*)}")
_OVERLAY_ASSET_RE = re.compile(r"(?P<base>.+)[_-](?P<number>\d+)(?P<suffix>\.[^.]+)$")
