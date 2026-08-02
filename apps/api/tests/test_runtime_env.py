import os

from lecturepilot.runtime_env import load_project_env


def test_load_project_env_reads_only_nearest_local_env_without_overriding(
    monkeypatch, tmp_path
) -> None:
    (tmp_path / ".env").write_text(
        "LECTUREPILOT_MODEL=openai/ambiguous-model\n",
        encoding="utf-8",
    )
    (tmp_path / ".env.local").write_text(
        "LECTUREPILOT_MODEL=openrouter/test-model\nGEMINI_API_KEY=from-dotenv\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("LECTUREPILOT_MODEL", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "from-shell")

    load_project_env()

    assert os.getenv("LECTUREPILOT_MODEL") == "openrouter/test-model"
    assert os.getenv("GEMINI_API_KEY") == "from-shell"


def test_load_project_env_does_not_load_local_secrets_in_production(monkeypatch, tmp_path) -> None:
    (tmp_path / ".env").write_text(
        "OPENAI_API_KEY=ambiguous-development-secret\n",
        encoding="utf-8",
    )
    (tmp_path / ".env.local").write_text(
        "OPENAI_API_KEY=local-development-secret\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LECTUREPILOT_ENV", "production")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    load_project_env()

    assert os.getenv("OPENAI_API_KEY") is None
