from __future__ import annotations

import os
from pathlib import Path


def default_workspace_root() -> Path:
    configured = os.environ.get("LECTUREPILOT_WORKSPACE_ROOT")
    return Path(configured or ".lecturepilot/workspaces").expanduser()


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
    "lecture-01": "Lecture01-eng.tex",
    "lecture-02": "Lecture02-eng.tex",
    "lecture-03": "Lecture03-eng.tex",
}
