from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote, unquote

from lecturepilot.course_source_routing_models import CourseSourceRoute, SourceRouteRole
from lecturepilot.models import Lecture
from lecturepilot.source_index_models import CourseSourceIndex, IndexedSourceFile
from lecturepilot.storage_layout import StorageLayout
from lecturepilot.latex_dependency_bundle import resolve_latex_compiler_inputs
from lecturepilot.workspace_fs import WorkspaceFSError


_TEXT = {
    ".md",
    ".json",
    ".jsonl",
    ".yaml",
    ".yml",
    ".tex",
    ".sty",
    ".cls",
    ".txt",
    ".html",
    ".css",
    ".svg",
    ".bib",
    ".ipynb",
    ".py",
    ".js",
    ".xml",
}


def retained_source_paths(
    layout: StorageLayout,
    course_id: str,
    index: CourseSourceIndex,
    routes: list[CourseSourceRoute],
    lectures: list[Lecture],
) -> set[str]:
    """Conservatively retain referenced evidence, including transitive assets."""
    keep = {r.path for r in routes if r.role != SourceRouteRole.EXCLUDED}
    indexed = {f.path for f in index.files}
    keep.update(l.material_path for l in lectures if l.material_path in indexed)
    uploads = layout.course_uploads_dir(course_id)
    roots = [layout.course_root(course_id) / name for name in ("canvas", "canvas-drafts")]
    # Preserve published/draft source manifests and approved learning evidence.
    builder = layout.course_root(course_id) / "builder"
    roots.extend(
        builder / name
        for name in ("source-manifests", "practice-designs", "learning-maps", "authoring-jobs")
    )
    for base in (layout.root / "users", layout.root / "previews" / "professors"):
        if base.exists():
            roots.extend(p / "courses" / course_id for p in base.iterdir() if p.is_dir())
    evidence = "\n".join(_read(path) for root in roots for path in _text_files(root))
    keep.update(_referenced(index.files, evidence))
    pending = list(keep)
    seen: set[str] = set()
    by_path = {item.path: item for item in index.files}
    while pending:
        path = pending.pop()
        if path in seen:
            continue
        seen.add(path)
        item = by_path[path]
        dependencies = set()
        if item.kind == "latex":
            dependencies.update(
                f.path
                for f in resolve_latex_compiler_inputs(
                    source_root=uploads, source_index=index, source_path=path
                )
            )
        if Path(path).suffix.lower() in _TEXT:
            dependencies.update(_referenced(index.files, _read(uploads / path)))
        dependencies.difference_update(keep)
        keep.update(dependencies)
        pending.extend(dependencies)
    return keep


def _referenced(files: list[IndexedSourceFile], text: str) -> set[str]:
    # Decode URL and JSON spelling before matching; basenames deliberately
    # over-retain ambiguous references rather than break a source link.
    text = unquote(text)
    return {
        item.path
        for item in files
        if any(
            token in text
            for token in (
                item.path,
                Path(item.path).name,
                json.dumps(item.path, ensure_ascii=True)[1:-1],
                quote(item.path),
                item.sha256,
            )
        )
    }


def _text_files(root: Path):
    if root.is_symlink():
        raise WorkspaceFSError("Source retention cannot inspect symbolic links.")
    if not root.exists():
        return
    for path in root.rglob("*"):
        if path.is_symlink():
            raise WorkspaceFSError("Source retention cannot inspect symbolic links.")
        if path.is_file() and path.suffix.lower() in _TEXT:
            yield path


def _read(path: Path) -> str:
    if path.is_symlink():
        raise WorkspaceFSError("Source retention cannot inspect symbolic links.")
    return path.read_text(encoding="utf-8", errors="replace")
