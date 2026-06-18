from __future__ import annotations

import json
import re
from pathlib import Path

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.canvas_component_blocks import write_component_sources
from lecturepilot.canvas_markdown_blocks import block_to_markdown, read_blocks


class CanvasMarkdownError(RuntimeError):
    pass
def write_document_source(document: CanvasDocument, canvas_dir: Path) -> None:
    canvas_dir.mkdir(parents=True, exist_ok=True)
    (canvas_dir / "sections").mkdir(exist_ok=True)
    _write_manifest(document, canvas_dir / "index.md")
    for index, section in enumerate(document.sections, start=1):
        section_path = canvas_dir / "sections" / f"{index:02d}-{_safe_filename(section.id)}.md"
        write_section_source(section, section_path, canvas_dir=canvas_dir)


def write_student_sections(canvas_dir: Path, sections: list[CanvasSection]) -> None:
    student_dir = canvas_dir / "student"
    student_dir.mkdir(parents=True, exist_ok=True)
    for section in sections:
        path = _find_section_path(student_dir, section.id) or _new_student_path(
            student_dir,
            section.id,
        )
        write_section_source(section, path, canvas_dir=canvas_dir)


def read_document_source(canvas_dir: Path) -> CanvasDocument:
    manifest = _read_frontmatter((canvas_dir / "index.md").read_text(encoding="utf-8"))[0]
    sections = _merged_sections(
        [
            *_read_section_dir(canvas_dir / "sections", manifest),
            *_read_section_dir(canvas_dir / "student", manifest),
        ]
    )
    return CanvasDocument(
        id=_required(manifest, "id"),
        import_version=int(manifest.get("import_version", 1)),
        course_id=_required(manifest, "course_id"),
        lecture_id=_required(manifest, "lecture_id"),
        title=_required(manifest, "title"),
        source_kind=_required(manifest, "source_kind"),
        source_ref=_required(manifest, "source_ref"),
        workspace_path=str(canvas_dir / "index.md"),
        sections=sections,
        warnings=_string_list(manifest.get("warnings")),
    )


def write_section_source(
    section: CanvasSection,
    path: Path,
    *,
    canvas_dir: Path | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if canvas_dir is not None:
        write_component_sources(section, canvas_dir)
    path.write_text(_section_to_markdown(section), encoding="utf-8")


def _write_manifest(document: CanvasDocument, path: Path) -> None:
    frontmatter = {
        "id": document.id,
        "import_version": document.import_version,
        "course_id": document.course_id,
        "lecture_id": document.lecture_id,
        "title": document.title,
        "source_kind": document.source_kind,
        "source_ref": document.source_ref,
        "warnings": document.warnings,
    }
    path.write_text(_frontmatter(frontmatter) + "\n", encoding="utf-8")


def _section_to_markdown(section: CanvasSection) -> str:
    header = _frontmatter(
        {
            "id": section.id,
            "title": section.title,
            "source_ref": section.source_ref or "",
        }
    )
    blocks = [_block_to_markdown(block) for block in section.blocks]
    return header + "\n\n".join(block for block in blocks if block).strip() + "\n"


def _block_to_markdown(block: CanvasBlock) -> str:
    return block_to_markdown(block)


def _read_section_dir(path: Path, manifest: dict[str, str]) -> list[CanvasSection]:
    if not path.exists():
        return []
    return [_read_section(path_item, manifest) for path_item in sorted(path.glob("*.md"))]


def _read_section(path: Path, manifest: dict[str, str]) -> CanvasSection:
    frontmatter, body = _read_frontmatter(path.read_text(encoding="utf-8"))
    section_id = _required(frontmatter, "id")
    return CanvasSection(
        id=section_id,
        title=_required(frontmatter, "title"),
        source_ref=frontmatter.get("source_ref") or None,
        blocks=read_blocks(
            body,
            section_id=section_id,
            course_id=_required(manifest, "course_id"),
            lecture_id=_required(manifest, "lecture_id"),
            components_dir=path.parent.parent / "components",
        ),
    )


def _read_frontmatter(text: str) -> tuple[dict[str, object], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        raise CanvasMarkdownError("Canvas Markdown frontmatter is not closed.")
    return _parse_frontmatter(text[4:end]), text[end + 4 :].strip()


def _parse_frontmatter(raw: str) -> dict[str, object]:
    result = {}
    for line in raw.splitlines():
        if not line.strip():
            continue
        key, _, value = line.partition(":")
        result[key.strip()] = _parse_value(value.strip())
    return result


def _parse_value(value: str) -> object:
    if value.startswith(('"', "[", "{")):
        return json.loads(value)
    return value


def _frontmatter(values: dict[str, object]) -> str:
    lines = ["---"]
    for key, value in values.items():
        lines.append(f"{key}: {json.dumps(value)}")
    return "\n".join([*lines, "---\n"])


def _required(values: dict[str, object], key: str) -> str:
    value = values.get(key)
    if value in (None, ""):
        raise CanvasMarkdownError(f"Canvas Markdown is missing {key}.")
    return str(value)


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item)[:500] for item in value if str(item).strip()]


def _find_section_path(path: Path, section_id: str) -> Path | None:
    for candidate in sorted(path.glob("*.md")):
        frontmatter, _ = _read_frontmatter(candidate.read_text(encoding="utf-8"))
        if frontmatter.get("id") == section_id:
            return candidate
    return None


def _new_student_path(path: Path, section_id: str) -> Path:
    return path / f"{90 + len(list(path.glob('*.md'))):02d}-{_safe_filename(section_id)}.md"


def _merged_sections(sections: list[CanvasSection]) -> list[CanvasSection]:
    result: list[CanvasSection] = []
    by_id: dict[str, int] = {}
    for section in sections:
        if section.id in by_id:
            result[by_id[section.id]] = section
        else:
            by_id[section.id] = len(result)
            result.append(section)
    return result


def _safe_filename(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "-", value).strip("-")[:120] or "section"
