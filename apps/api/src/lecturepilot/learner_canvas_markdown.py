from __future__ import annotations

import re
from pathlib import Path

from lecturepilot.canvas_markdown import (
    CanvasMarkdownError,
    read_section_frontmatter,
    read_section_source,
    section_to_markdown,
)
from lecturepilot.canvas_models import CanvasSection
from lecturepilot.durable_files import atomic_write_text


def write_student_sections(
    canvas_dir: Path,
    sections: list[CanvasSection],
    placements: dict[str, object] | None = None,
) -> None:
    student_dir = canvas_dir / "student"
    student_dir.mkdir(parents=True, exist_ok=True)
    current = read_student_section_placements(canvas_dir)
    requested = dict(current)
    for section_id, placement in (placements or {}).items():
        value = _placement_value(placement)
        if value is None:
            requested.pop(section_id, None)
        else:
            requested[section_id] = value
    written_ids = set()
    for section in sections:
        path = _find_section_path(student_dir, section.id) or _new_student_path(
            student_dir, section.id
        )
        _write_student_section(path, section, requested.get(section.id))
        written_ids.add(section.id)
    for section_id in set((placements or {})) - written_ids:
        path = _find_section_path(student_dir, section_id)
        if path is None:
            raise CanvasMarkdownError(
                f"Learner placement references unknown section '{section_id}'."
            )
        section = read_section_source(
            path,
            course_id="learner-overlay",
            lecture_id="learner-overlay",
            external_components=False,
        )
        _write_student_section(path, section, requested.get(section_id))


def read_student_sections(
    canvas_dir: Path, *, course_id: str, lecture_id: str
) -> list[CanvasSection]:
    path = canvas_dir / "student"
    if not path.exists():
        return []
    return [
        read_section_source(
            item,
            course_id=course_id,
            lecture_id=lecture_id,
            external_components=False,
        )
        for item in sorted(path.glob("*.md"))
    ]


def read_student_section_placements(canvas_dir: Path) -> dict[str, dict[str, str]]:
    path = canvas_dir / "student"
    if not path.exists():
        return {}
    result: dict[str, dict[str, str]] = {}
    for item in sorted(path.glob("*.md")):
        frontmatter = read_section_frontmatter(item)
        section_id = _required_string(frontmatter, "id")
        mode = frontmatter.get("placement_mode")
        anchor = frontmatter.get("placement_section_id")
        if mode is None and anchor is None:
            continue
        if mode not in {"after_section", "before_section"} or not isinstance(anchor, str):
            raise CanvasMarkdownError(
                f"Learner section '{section_id}' has invalid placement frontmatter."
            )
        result[section_id] = {"mode": mode, "section_id": anchor}
    return result


def place_student_sections(
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


def _write_student_section(
    path: Path, section: CanvasSection, placement: dict[str, str] | None
) -> None:
    placement_fields = (
        {
            "placement_mode": placement["mode"],
            "placement_section_id": placement["section_id"],
        }
        if placement
        else None
    )
    atomic_write_text(
        path,
        section_to_markdown(
            section,
            extra_frontmatter=placement_fields,
            inline_components=True,
        ),
    )


def _placement_value(placement: object) -> dict[str, str] | None:
    if placement is None:
        return None
    mode = getattr(placement, "mode", None)
    section_id = getattr(placement, "section_id", None)
    if isinstance(placement, dict):
        mode = placement.get("mode")
        section_id = placement.get("section_id")
    if mode not in {"after_section", "before_section"} or not isinstance(section_id, str):
        raise CanvasMarkdownError("Learner section placement is invalid.")
    return {"mode": mode, "section_id": section_id}


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


def _find_section_path(path: Path, section_id: str) -> Path | None:
    for candidate in sorted(path.glob("*.md")):
        if read_section_frontmatter(candidate).get("id") == section_id:
            return candidate
    return None


def _new_student_path(path: Path, section_id: str) -> Path:
    safe_name = re.sub(r"[^a-zA-Z0-9_-]+", "-", section_id).strip("-")[:120] or "section"
    return path / f"{90 + len(list(path.glob('*.md'))):02d}-{safe_name}.md"


def _required_string(values: dict[str, object], key: str) -> str:
    value = values.get(key)
    if not isinstance(value, str) or not value:
        raise CanvasMarkdownError(f"Canvas Markdown is missing {key}.")
    return value


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
