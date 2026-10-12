"""Reuse section drafts whose teaching inputs a teaching repair left unchanged.

Besides shared instructions, a section author sees only its own evidence, its assigned approved
targets, the lecture objective and planning context (`section_contracts`; the design revision
appears there only as an opaque id). The digest of exactly those inputs is recorded per draft,
so after a design-conflict teaching repair only sections whose digest changed are written
again; every reused draft still passes the deterministic checks of the new implementation
revision, and the generated draft binds to that new revision.
"""

from hashlib import sha256
import json
from pathlib import Path

from lecturepilot.canvas_markdown import section_to_markdown
from lecturepilot.durable_files import atomic_write_json

SECTION_INPUTS = "section-inputs.json"


def section_inputs(job, workspace) -> dict[str, str]:
    shared = {
        "schema": 1,
        "source_revision": job.source_revision,
        "model": job.settings.model,
        "language": job.output_language,
        "objective": job.design.objective,
        "planning_context": job.design.planning_context.model_dump(mode="json"),
    }
    inputs = {}
    for index, (path, section) in enumerate(workspace.paths.items()):
        payload = {
            **shared,
            "first": index == 0,
            "evidence": section_to_markdown(section, inline_components=True),
            "targets": [target.model_dump(mode="json") for target in workspace.targets[section.id]],
        }
        inputs[path] = sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return inputs


def record_section_inputs(root: Path, inputs: dict[str, str]) -> None:
    atomic_write_json(root / SECTION_INPUTS, inputs)


def reuse_unaffected_sections(workspace, inputs: dict[str, str], previous_root: Path) -> int:
    """Copy missing drafts from the previous implementation's job when inputs match exactly."""
    recorded = previous_root / SECTION_INPUTS
    if not recorded.is_file():
        return 0  # Jobs saved before per-section digests are regenerated in full.
    previous = json.loads(recorded.read_text())
    reused = 0
    for path, digest in inputs.items():
        draft = previous_root / "draft" / Path(path).name
        if (
            previous.get(path) != digest
            or not draft.is_file()
            or workspace.fs.resolve(path, for_write=True).path.exists()
        ):
            continue
        workspace.write(path, draft.read_text())
        reused += 1
    return reused
