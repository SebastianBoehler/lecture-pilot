from pathlib import Path

import pytest

from lecturepilot.canvas_workspace import _default_material_root


def test_default_material_root_prefers_repo_local_copy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    local_root = tmp_path / "local-course-materials" / "martius-ml"
    local_root.mkdir(parents=True)
    (local_root / "Lecture03-eng.tex").write_text("local demo source", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("LECTUREPILOT_COURSE_MATERIAL_ROOT", raising=False)

    assert _default_material_root().resolve() == local_root.resolve()
