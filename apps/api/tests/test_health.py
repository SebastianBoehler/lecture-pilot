from importlib.metadata import version as package_version
from pathlib import Path

from fastapi.testclient import TestClient

import lecturepilot.release_info as release_info_module
from lecturepilot.app import create_app


def test_health_endpoint(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(release_info_module, "_BUILD_COMMIT_PATH", tmp_path / "missing")
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "version": package_version("lecturepilot-api"),
        "commit_sha": "unknown",
    }


def test_health_endpoint_exposes_baked_release_identity(tmp_path: Path, monkeypatch) -> None:
    build_commit = tmp_path / "build-commit.txt"
    build_commit.write_text("b7f559d4a3c2\n", encoding="ascii")
    monkeypatch.setattr(release_info_module, "_BUILD_COMMIT_PATH", build_commit)
    monkeypatch.setenv("LECTUREPILOT_RELEASE_VERSION", "9.9.9-runtime-override")
    monkeypatch.setenv("LECTUREPILOT_COMMIT_SHA", "b7f559d4a3c2")
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "version": package_version("lecturepilot-api"),
        "commit_sha": "b7f559d4a3c2",
    }


def test_health_endpoint_rejects_invalid_baked_release_identity(
    tmp_path: Path, monkeypatch
) -> None:
    build_commit = tmp_path / "build-commit.txt"
    build_commit.write_text("not-a-commit\n", encoding="ascii")
    monkeypatch.setattr(release_info_module, "_BUILD_COMMIT_PATH", build_commit)
    monkeypatch.setenv("LECTUREPILOT_COMMIT_SHA", "b7f559d4a3c2")
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {
        "status": "error",
        "version": package_version("lecturepilot-api"),
        "commit_sha": "unknown",
    }


def test_health_endpoint_rejects_stale_baked_release_identity(tmp_path: Path, monkeypatch) -> None:
    build_commit = tmp_path / "build-commit.txt"
    build_commit.write_text("aaaaaaaaaaaa\n", encoding="ascii")
    monkeypatch.setattr(release_info_module, "_BUILD_COMMIT_PATH", build_commit)
    monkeypatch.setenv("LECTUREPILOT_COMMIT_SHA", "bbbbbbbbbbbb")
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {
        "status": "error",
        "version": package_version("lecturepilot-api"),
        "commit_sha": "aaaaaaaaaaaa",
    }
