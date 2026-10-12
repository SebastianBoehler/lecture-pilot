"""Rewrite legacy generated learning-support boilerplate in stored canvases once.

Early generators wrote fixed English "Why this matters", study-list and "Learning checkpoint"
copy into official canvas sections. Reads used to rewrite that copy on every access; this
migration rewrites the stored Markdown to exactly what those reads returned, so draft digests,
learning maps and publication bindings stay valid. Run it while the API is stopped. It is a
dry run unless ``apply=True`` and is idempotent.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
import re

from lecturepilot.canvas.canvas_markdown import (
    CanvasMarkdownError,
    _read_frontmatter,
    parse_section_frontmatter,
    read_section_source,
)
from lecturepilot.canvas.canvas_markdown_blocks import block_to_markdown, read_blocks
from lecturepilot.canvas.canvas_models import CanvasBlock, CanvasSection
from lecturepilot.canvas.canvas_snapshot import locked_canvas_paths
from lecturepilot.core.durable_files import atomic_write_text


_LEGACY_CHECKPOINT_RE = re.compile(
    r"^Learning checkpoint: use .+? to rephrase the section without slide wording\. "
    r"A good answer should include the mechanism, a concrete example, and one limitation or "
    r"failure mode\.$",
    re.DOTALL,
)
_LEGACY_WHY_RE = re.compile(
    r"^\*\*Why this matters\.\*\* .+? turns the source material into a decision step\. "
    r"The key cue is (?P<anchor>.+?)\. Use it to identify the quantity being estimated, "
    r"state what evidence changes it, and connect the result to the decision the learner must make\.$",
    re.DOTALL,
)
_LEGACY_STUDY_ITEMS = [
    "Name the source variable or formula before interpreting it.",
    "Explain which part comes from evidence and which part is a modeling choice.",
    "Check how the conclusion would change under a different cost or observation.",
]
_STUDY_ITEMS = [
    "Identify the relevant variable, formula, metric, or case before interpreting it.",
    "Separate what is observed in the data from what is chosen by the modeler.",
    "Describe how the conclusion would change under a different threshold, cost, or observation.",
]


def migrate(storage_root: Path, *, apply: bool = False) -> dict:
    report: dict = {
        "migration": "canvas_boilerplate",
        "applied": apply,
        "canvases_scanned": 0,
        "changed_files": [],
        "unmatched_files": [],
        "errors": [],
    }
    for canvas_dir in stored_course_canvas_dirs(storage_root):
        report["canvases_scanned"] += 1
        try:
            with locked_canvas_paths(canvas_dir):
                _migrate_canvas(canvas_dir, storage_root, report, apply=apply)
        except (CanvasMarkdownError, OSError, ValueError) as exc:
            report["errors"].append(f"{canvas_dir.relative_to(storage_root)}: {exc}")
    return report


def stored_course_canvas_dirs(storage_root: Path) -> Iterator[Path]:
    """Published and draft course canvases below ``courses/<tenant>/<course>/``."""
    for course_root in sorted((storage_root / "courses").glob("*/*")):
        yield from _with_index(sorted((course_root / "canvas" / "lectures").glob("*")))
        drafts = sorted((course_root / "canvas-drafts" / "lectures").glob("*/latest"))
        yield from _with_index(drafts)


def _with_index(paths: list[Path]) -> Iterator[Path]:
    return (path for path in paths if (path / "index.md").is_file())


def _migrate_canvas(canvas_dir: Path, storage_root: Path, report: dict, *, apply: bool) -> None:
    manifest = parse_section_frontmatter((canvas_dir / "index.md").read_text(encoding="utf-8"))
    ids = {"course_id": str(manifest["course_id"]), "lecture_id": str(manifest["lecture_id"])}
    for path in sorted((canvas_dir / "sections").glob("*.md")):
        section = read_section_source(path, external_components=True, **ids)
        expected = _normalized_section(section)
        if expected == section:
            continue
        relative = str(path.relative_to(storage_root))
        rewritten = _rewritten_text(path, section, expected, ids)
        if rewritten is None:
            report["unmatched_files"].append(relative)
            continue
        report["changed_files"].append(relative)
        if apply:
            atomic_write_text(path, rewritten)


def _rewritten_text(
    path: Path, section: CanvasSection, expected: CanvasSection, ids: dict[str, str]
) -> str | None:
    text = path.read_text(encoding="utf-8")
    for old, new in zip(section.blocks, expected.blocks, strict=True):
        if old == new:
            continue
        old_body, new_body = _body(old), _body(new)
        if text.count(old_body) != 1:
            return None
        text = text.replace(old_body, new_body)
    frontmatter, body = _read_frontmatter(text)
    blocks = read_blocks(
        body,
        section_id=str(frontmatter["id"]),
        components_dir=path.parent.parent / "components",
        **ids,
    )
    return text if blocks == expected.blocks else None


def _body(block: CanvasBlock) -> str:
    return block_to_markdown(block).split("\n", 1)[1]


def _normalized_section(section: CanvasSection) -> CanvasSection:
    blocks = [_normalized_block(block, section.title) for block in section.blocks]
    return section.model_copy(update={"blocks": blocks})


def _normalized_block(block: CanvasBlock, title: str) -> CanvasBlock:
    if block.type == "list" and block.items == _LEGACY_STUDY_ITEMS:
        return block.model_copy(update={"items": list(_STUDY_ITEMS)})
    if not block.text:
        return block
    if block.type == "paragraph" and (match := _LEGACY_WHY_RE.match(block.text.strip())):
        return block.model_copy(update={"text": _why_text(title, match.group("anchor"))})
    if block.type == "callout" and _LEGACY_CHECKPOINT_RE.match(block.text.strip()):
        return block.model_copy(update={"text": _check_prompt(title)})
    return block


def _why_text(title: str, anchor: str) -> str:
    return (
        f"**Why this matters.** {title} is useful when the concept changes a decision, "
        f"estimate, or model comparison. Focus on {anchor}. Ask what quantity or case is being "
        "estimated, what evidence changes it, and what action would change if the answer changed."
    )


def _check_prompt(title: str) -> str:
    return (
        f"Check yourself: In **{title}**, what would you compute or compare first, and why? "
        "Answer with one concrete example from this section and one limitation or failure mode."
    )
