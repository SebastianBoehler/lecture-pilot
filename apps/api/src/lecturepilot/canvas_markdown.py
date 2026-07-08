from __future__ import annotations

import json
import re
from pathlib import Path

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.canvas_component_blocks import write_component_sources
from lecturepilot.canvas_markdown_blocks import block_to_markdown, read_blocks

_PLACEMENT_FILE = "placement.json"


class CanvasMarkdownError(RuntimeError):
    pass


def write_document_source(document: CanvasDocument, canvas_dir: Path) -> None:
    canvas_dir.mkdir(parents=True, exist_ok=True)
    (canvas_dir / "sections").mkdir(exist_ok=True)
    _write_manifest(document, canvas_dir / "index.md")
    for index, section in enumerate(document.sections, start=1):
        section_path = canvas_dir / "sections" / f"{index:02d}-{_safe_filename(section.id)}.md"
        write_section_source(section, section_path, canvas_dir=canvas_dir)


def write_student_sections(
    canvas_dir: Path,
    sections: list[CanvasSection],
    placements: dict[str, object] | None = None,
) -> None:
    student_dir = canvas_dir / "student"
    student_dir.mkdir(parents=True, exist_ok=True)
    for section in sections:
        path = _find_section_path(student_dir, section.id) or _new_student_path(
            student_dir,
            section.id,
        )
        write_section_source(section, path, canvas_dir=canvas_dir)
    if placements is not None:
        _write_section_placements(canvas_dir, placements)


def read_student_section_placements(canvas_dir: Path) -> dict[str, dict[str, str]]:
    return _read_section_placements(canvas_dir)


def read_document_source(canvas_dir: Path) -> CanvasDocument:
    manifest = _read_frontmatter((canvas_dir / "index.md").read_text(encoding="utf-8"))[0]
    sections = _placed_sections(
        _read_section_dir(canvas_dir / "sections", manifest),
        _read_section_dir(canvas_dir / "student", manifest),
        _read_section_placements(canvas_dir),
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


def _read_section_placements(canvas_dir: Path) -> dict[str, dict[str, str]]:
    path = canvas_dir / _PLACEMENT_FILE
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    return {
        str(section_id): {"mode": str(value["mode"]), "section_id": str(value["section_id"])}
        for section_id, value in payload.items()
        if isinstance(value, dict)
        and value.get("mode") in {"after_section", "before_section"}
        and isinstance(value.get("section_id"), str)
    }


def _write_section_placements(canvas_dir: Path, placements: dict[str, object]) -> None:
    existing = _read_section_placements(canvas_dir)
    for section_id, placement in placements.items():
        value = _placement_value(placement)
        if value is None:
            existing.pop(section_id, None)
        else:
            existing[section_id] = value
    path = canvas_dir / _PLACEMENT_FILE
    if not existing:
        path.unlink(missing_ok=True)
        return
    path.write_text(json.dumps(existing, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _placement_value(placement: object) -> dict[str, str] | None:
    mode = getattr(placement, "mode", None)
    section_id = getattr(placement, "section_id", None)
    if isinstance(placement, dict):
        mode = placement.get("mode")
        section_id = placement.get("section_id")
    if mode not in {"after_section", "before_section"} or not isinstance(section_id, str):
        return None
    return {"mode": str(mode), "section_id": section_id}


def _placed_sections(
    base_sections: list[CanvasSection],
    student_sections: list[CanvasSection],
    placements: dict[str, dict[str, str]],
) -> list[CanvasSection]:
    result = _merged_sections(base_sections)
    unplaced: list[CanvasSection] = []
    for section in _merged_sections(student_sections):
        placement = placements.get(section.id)
        insert_at = _placement_index(result, placement, placements) if placement else None
        if insert_at is None:
            unplaced.append(section)
        else:
            result.insert(insert_at, section)
    return _merged_sections([*result, *unplaced])


def _placement_index(
    sections: list[CanvasSection],
    placement: dict[str, str],
    placements: dict[str, dict[str, str]],
) -> int | None:
    for index, section in enumerate(sections):
        if section.id != placement["section_id"]:
            continue
        if placement["mode"] == "before_section":
            return index
        insert_at = index + 1
        while insert_at < len(sections) and placements.get(sections[insert_at].id) == placement:
            insert_at += 1
        return insert_at
    return None


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
