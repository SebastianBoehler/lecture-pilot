from __future__ import annotations

import json
import re
from pathlib import Path

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection


class CanvasMarkdownError(RuntimeError):
    pass

def write_document_source(document: CanvasDocument, canvas_dir: Path) -> None:
    canvas_dir.mkdir(parents=True, exist_ok=True)
    (canvas_dir / "sections").mkdir(exist_ok=True)
    _write_manifest(document, canvas_dir / "index.md")
    for index, section in enumerate(document.sections, start=1):
        section_path = canvas_dir / "sections" / f"{index:02d}-{_safe_filename(section.id)}.md"
        write_section_source(section, section_path)


def write_student_sections(canvas_dir: Path, sections: list[CanvasSection]) -> None:
    student_dir = canvas_dir / "student"
    student_dir.mkdir(parents=True, exist_ok=True)
    for section in sections:
        path = _find_section_path(student_dir, section.id) or _new_student_path(student_dir, section.id)
        write_section_source(section, path)


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
    )


def write_section_source(section: CanvasSection, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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
    header = f'<!-- block id="{block.id}" type="{block.type}" -->'
    if block.type == "asset":
        target = block.asset_path or block.asset_url or ""
        caption = block.caption or block.asset_path or "Course figure"
        return f"{header}\n![{caption}](asset:{target})"
    if block.type == "list":
        return f"{header}\n" + "\n".join(f"- {item}" for item in block.items)
    if block.type == "math":
        return f"{header}\n```math\n{block.text or ''}\n```"
    if block.type == "callout":
        return f"{header}\n" + "\n".join(f"> {line}" for line in (block.text or "").splitlines())
    return f"{header}\n{block.text or ''}"


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
        blocks=_read_blocks(
            body,
            section_id=section_id,
            course_id=_required(manifest, "course_id"),
            lecture_id=_required(manifest, "lecture_id"),
        ),
    )


def _read_blocks(
    body: str,
    *,
    section_id: str,
    course_id: str,
    lecture_id: str,
) -> list[CanvasBlock]:
    matches = list(_BLOCK_RE.finditer(body))
    if not matches:
        return _read_unmarked_blocks(body, section_id=section_id, course_id=course_id, lecture_id=lecture_id)
    blocks = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        blocks.append(
            _read_block(
                match.group("id"),
                match.group("type"),
                body[start:end].strip(),
                section_id=section_id,
                course_id=course_id,
                lecture_id=lecture_id,
            )
        )
    return blocks


def _read_unmarked_blocks(
    body: str,
    *,
    section_id: str,
    course_id: str,
    lecture_id: str,
) -> list[CanvasBlock]:
    blocks = []
    chunks = [chunk.strip() for chunk in re.split(r"\n\s*\n", body) if chunk.strip()]
    counters: dict[str, int] = {}
    for chunk in chunks:
        block_type = _infer_block_type(chunk)
        counters[block_type] = counters.get(block_type, 0) + 1
        block_id = f"{section_id}-{_type_suffix(block_type)}-{counters[block_type]}"
        blocks.append(
            _read_block(
                block_id,
                block_type,
                chunk,
                section_id=section_id,
                course_id=course_id,
                lecture_id=lecture_id,
            )
        )
    return blocks


def _read_block(
    block_id: str,
    block_type: str,
    chunk: str,
    *,
    section_id: str,
    course_id: str,
    lecture_id: str,
) -> CanvasBlock:
    if block_type == "asset":
        match = _IMAGE_RE.search(chunk)
        target = match.group("target") if match else ""
        asset_path = target.removeprefix("asset:")
        return CanvasBlock(
            id=block_id,
            type="asset",
            asset_path=asset_path,
            asset_url=f"/course-assets/{course_id}/{lecture_id}/{asset_path}",
            caption=match.group("caption") if match else asset_path,
        )
    if block_type == "list":
        return CanvasBlock(id=block_id, type="list", items=_read_list_items(chunk))
    if block_type == "math":
        return CanvasBlock(id=block_id, type="math", text=_read_math(chunk))
    if block_type == "callout":
        return CanvasBlock(id=block_id, type="callout", text=_read_callout(chunk))
    if block_type != "paragraph":
        raise CanvasMarkdownError(f"Unsupported canvas block type: {block_type}")
    return CanvasBlock(id=block_id, type="paragraph", text=chunk.strip())


def _read_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        raise CanvasMarkdownError("Canvas Markdown frontmatter is not closed.")
    return _parse_frontmatter(text[4:end]), text[end + 4 :].strip()


def _parse_frontmatter(raw: str) -> dict[str, str]:
    result = {}
    for line in raw.splitlines():
        if not line.strip():
            continue
        key, _, value = line.partition(":")
        result[key.strip()] = _parse_value(value.strip())
    return result


def _parse_value(value: str) -> str:
    if value.startswith('"'):
        return str(json.loads(value))
    return value


def _frontmatter(values: dict[str, object]) -> str:
    lines = ["---"]
    for key, value in values.items():
        lines.append(f"{key}: {json.dumps(value)}")
    return "\n".join([*lines, "---\n"])


def _required(values: dict[str, str], key: str) -> str:
    value = values.get(key)
    if value in (None, ""):
        raise CanvasMarkdownError(f"Canvas Markdown is missing {key}.")
    return value


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


def _read_list_items(chunk: str) -> list[str]:
    return [line[2:].strip() for line in chunk.splitlines() if line.startswith("- ")]


def _read_math(chunk: str) -> str:
    match = _MATH_RE.search(chunk)
    return (match.group("formula") if match else chunk).strip()


def _read_callout(chunk: str) -> str:
    return "\n".join(line.removeprefix("> ").strip() for line in chunk.splitlines()).strip()


def _infer_block_type(chunk: str) -> str:
    if _IMAGE_RE.search(chunk):
        return "asset"
    if chunk.startswith("```math"):
        return "math"
    if all(line.startswith("- ") for line in chunk.splitlines()):
        return "list"
    if all(line.startswith(">") for line in chunk.splitlines()):
        return "callout"
    return "paragraph"


def _type_suffix(block_type: str) -> str:
    return {"paragraph": "p", "list": "list", "asset": "asset", "callout": "callout", "math": "math"}[block_type]


def _safe_filename(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "-", value).strip("-")[:120] or "section"

_BLOCK_RE = re.compile(r'<!--\s*block\s+id="(?P<id>[^"]+)"\s+type="(?P<type>[^"]+)"\s*-->')
_IMAGE_RE = re.compile(r"!\[(?P<caption>[^]]*)]\((?P<target>[^)]+)\)")
_MATH_RE = re.compile(r"```math\s*(?P<formula>.*?)```", re.DOTALL)
