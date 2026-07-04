from __future__ import annotations

import os
from pathlib import Path


SEEDED_COURSE_ID = "martius-ml"


def default_workspace_root() -> Path:
    configured = os.environ.get("LECTUREPILOT_WORKSPACE_ROOT")
    return Path(configured or ".lecturepilot").expanduser()


def default_material_root() -> Path:
    configured = os.environ.get("LECTUREPILOT_COURSE_MATERIAL_ROOT")
    if configured:
        return Path(configured).expanduser()
    local_materials = Path("local-course-materials/martius-ml").expanduser()
    if (local_materials / "Lecture03-eng.tex").exists():
        return local_materials
    candidates = Path.home().glob(
        "Documents/Studium/*/Kurse/Grundlagen des Maschinellen Lernens Vorlesung"
    )
    for candidate in candidates:
        if (candidate / "Lecture03-eng.tex").exists():
            return candidate
    return Path("local-course-materials/martius-ml").expanduser()


def lecture_source_name(lecture_id: str) -> str | None:
    return _LECTURE_SOURCES.get(lecture_id)


_LECTURE_SOURCES = {
    f"lecture-{index:02d}": f"Lecture{index:02d}-eng.tex"
    for index in range(1, 81)
}
