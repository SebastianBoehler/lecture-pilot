import re
import tomllib
from pathlib import Path


CONVERTER_ROOT = Path(__file__).resolve().parents[1]
EXACT_DEPENDENCY = re.compile(r"^([A-Za-z0-9_.-]+)(?:\[[^]]+\])?==([^; ]+)$")


def _normalized_package(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def test_container_constraints_match_exact_runtime_dependencies() -> None:
    project = tomllib.loads((CONVERTER_ROOT / "pyproject.toml").read_text())
    constraints = {
        _normalized_package(match.group(1)): match.group(2)
        for line in (CONVERTER_ROOT / "requirements.lock").read_text().splitlines()
        if (match := EXACT_DEPENDENCY.fullmatch(line))
    }

    for dependency in project["project"]["dependencies"]:
        match = EXACT_DEPENDENCY.fullmatch(dependency)
        assert match is not None, f"runtime dependency must be pinned exactly: {dependency}"
        package = _normalized_package(match.group(1))
        assert constraints.get(package) == match.group(2), (
            f"container constraint for {package} does not match pyproject.toml"
        )
