from importlib.metadata import version as package_version
from pathlib import Path

from fastapi.testclient import TestClient

import lecturepilot.release_info as release_info_module
from lecturepilot.app import create_app
from lecturepilot.runtime_readiness import ReadinessResult


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


def test_readiness_endpoint_checks_runtime_dependencies() -> None:
    app = create_app()
    app.state.runtime_readiness = _Readiness(
        ReadinessResult(
            ready=True,
            checks={"database": "ok", "latex_compiler": "ok"},
        )
    )

    response = TestClient(app).get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "checks": {"database": "ok", "latex_compiler": "ok"},
    }


def test_readiness_endpoint_fails_closed_without_dependency_details() -> None:
    app = create_app()
    app.state.runtime_readiness = _Readiness(
        ReadinessResult(
            ready=False,
            checks={"database": "ok", "latex_compiler": "error"},
        )
    )

    response = TestClient(app).get("/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "error",
        "checks": {"database": "ok", "latex_compiler": "error"},
    }


class _Readiness:
    def __init__(self, result: ReadinessResult) -> None:
        self.result = result

    def check(self) -> ReadinessResult:
        return self.result
