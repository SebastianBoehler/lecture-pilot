from __future__ import annotations

import json
import re
from pathlib import Path

from lecturepilot.canvas_models import CanvasBlock, CanvasSection
from lecturepilot.latex_canvas_text import slug


MAX_NOTEBOOK_CELLS = 120
MAX_NOTEBOOK_CHARS = 60_000
MAX_MARKDOWN_CELL_CHARS = 6_000
MAX_CODE_CELL_CHARS = 12_000
MAX_CODE_FILE_CHARS = 60_000
_MARKDOWN_IMAGE_RE = re.compile(r"!\[(?P<label>[^]]*)]\([^)]+\)")


class SourceCodeCanvasError(RuntimeError):
    """Raised when notebook or code source cannot become safe Canvas evidence."""


def notebook_section(path: Path, source_ref: str) -> CanvasSection | None:
    notebook = _read_notebook(path)
    language = _notebook_language(notebook)
    blocks: list[CanvasBlock] = []
    remaining = MAX_NOTEBOOK_CHARS
    cells = notebook.get("cells")
    if not isinstance(cells, list):
        raise SourceCodeCanvasError(f"Could not read notebook {path.name}.")

    for index, cell in enumerate(cells[:MAX_NOTEBOOK_CELLS], start=1):
        if remaining <= 0 or not isinstance(cell, dict):
            break
        # Outputs and execution metadata are intentionally never copied into Canvas evidence.
        cell_type = cell.get("cell_type")
        source = _cell_source(cell.get("source"))
        if not source:
            continue
        if cell_type == "code":
            limit = min(remaining, MAX_CODE_CELL_CHARS)
            text = _code_fence(source[:limit], language)
        elif cell_type in {"markdown", "raw"}:
            limit = min(remaining, MAX_MARKDOWN_CELL_CHARS)
            text = _safe_markdown(source[:limit]).strip()
        else:
            continue
        if not text:
            continue
        blocks.append(
            CanvasBlock(
                id=f"{slug(source_ref)}-cell-{index}",
                type="paragraph",
                text=text,
            )
        )
        remaining -= len(text)

    if not blocks:
        return None
    return CanvasSection(
        id=slug(source_ref),
        title=_notebook_title(notebook, path),
        source_ref=source_ref,
        blocks=blocks,
    )


def code_section(path: Path, source_ref: str) -> CanvasSection | None:
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            source = handle.read(MAX_CODE_FILE_CHARS)
    except OSError as exc:
        raise SourceCodeCanvasError(f"Could not read code source {path.name}.") from exc
    if not source.strip():
        return None
    return CanvasSection(
        id=slug(source_ref),
        title=_filename_title(path),
        source_ref=source_ref,
        blocks=[
            CanvasBlock(
                id=f"{slug(source_ref)}-code-1",
                type="paragraph",
                text=_code_fence(source, _code_language(path)),
            )
        ],
    )


def _read_notebook(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SourceCodeCanvasError(f"Could not read notebook {path.name}.") from exc
    if not isinstance(payload, dict):
        raise SourceCodeCanvasError(f"Could not read notebook {path.name}.")
    return payload


def _cell_source(value: object) -> str:
    if isinstance(value, str):
        return value.replace("\x00", "")
    if isinstance(value, list):
        return "".join(item for item in value if isinstance(item, str)).replace("\x00", "")
    return ""


def _notebook_language(notebook: dict) -> str:
    metadata = notebook.get("metadata")
    if not isinstance(metadata, dict):
        return "text"
    language_info = metadata.get("language_info")
    kernelspec = metadata.get("kernelspec")
    candidates = [
        language_info.get("name") if isinstance(language_info, dict) else None,
        kernelspec.get("language") if isinstance(kernelspec, dict) else None,
    ]
    for candidate in candidates:
        if isinstance(candidate, str) and (language := _safe_language(candidate)):
            return language
    return "text"


def _notebook_title(notebook: dict, path: Path) -> str:
    cells = notebook.get("cells")
    if isinstance(cells, list):
        for cell in cells[:MAX_NOTEBOOK_CELLS]:
            if not isinstance(cell, dict) or cell.get("cell_type") != "markdown":
                continue
            source = _cell_source(cell.get("source"))
            if heading := re.search(r"^#{1,6}\s+(.+)$", source, re.MULTILINE):
                return heading.group(1).strip()[:200]
    return _filename_title(path)


def _code_fence(source: str, language: str) -> str:
    source = source.rstrip()
    longest = max((len(match.group(0)) for match in re.finditer(r"`+", source)), default=0)
    fence = "`" * max(3, longest + 1)
    return f"{fence}{language}\n{source}\n{fence}"


def _code_language(path: Path) -> str:
    return {".py": "python"}.get(path.suffix.lower(), "text")


def _safe_language(value: str) -> str:
    language = re.sub(r"[^a-zA-Z0-9_+-]", "", value).lower()[:30]
    return language


def _safe_markdown(value: str) -> str:
    return _MARKDOWN_IMAGE_RE.sub(lambda match: match.group("label") or "Notebook image", value)


def _filename_title(path: Path) -> str:
    return path.stem.replace("-", " ").replace("_", " ").title()[:200]
