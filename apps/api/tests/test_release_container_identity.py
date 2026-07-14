from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
API_DOCKERFILE = REPO_ROOT / "apps" / "api" / "Dockerfile"
COMPOSE = REPO_ROOT / "deploy" / "compose.yml"


def test_api_image_bakes_validated_commit_identity() -> None:
    dockerfile = API_DOCKERFILE.read_text(encoding="utf-8")

    assert "ARG LECTUREPILOT_COMMIT_SHA" in dockerfile
    assert "_build_commit.txt" in dockerfile
    assert "org.opencontainers.image.revision" in dockerfile


def test_compose_builds_and_preflights_the_same_commit_identity() -> None:
    compose = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    api_build = compose["x-api-build"]
    api_image = compose["x-api-image"]

    assert api_build["args"]["LECTUREPILOT_COMMIT_SHA"].startswith("${LECTUREPILOT_COMMIT_SHA:")
    for service in ("api", "preflight", "migrate"):
        assert compose["services"][service]["build"] == api_build
        assert compose["services"][service]["image"] == api_image
    assert "${LECTUREPILOT_COMMIT_SHA:" in api_image
    assert "--require-build-identity" in compose["services"]["preflight"]["command"]
