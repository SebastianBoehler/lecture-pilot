import os

from lecturepilot.runtime_env import load_project_env


def test_load_project_env_reads_nearest_dotenv_without_overriding(monkeypatch, tmp_path) -> None:
    (tmp_path / ".env").write_text(
        "LECTUREPILOT_MODEL=openrouter/test-model\n"
        "GEMINI_API_KEY=from-dotenv\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("LECTUREPILOT_MODEL", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "from-shell")

    load_project_env()

    assert os.getenv("LECTUREPILOT_MODEL") == "openrouter/test-model"
    assert os.getenv("GEMINI_API_KEY") == "from-shell"
