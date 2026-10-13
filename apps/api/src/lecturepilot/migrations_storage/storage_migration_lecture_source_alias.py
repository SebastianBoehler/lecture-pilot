"""One-time alias from course-wide to lecture-local source revisions.

Lecture source revisions used to hash the lecture's manifest plus the whole course's
provenance (every lecture's schedule entry, the full source index and the full routing,
mapped through the storage-only cleanup receipt). Any change anywhere therefore staled every
lecture's approvals, drafts and publications. Revisions are now lecture-local
(``lecturepilot.sources.lecture_source_revision``).

Stored approvals, draft bindings and publications are never rewritten. Instead this
migration records, for every lecture with a source manifest, the legacy revision the
runtime returned before the change and the new local revision of the same inputs in
``builder/source-manifests/<lecture>.alias.json`` whenever a stored file of the course
(design, draft binding, review, publication, repair or job record) refers to that legacy
value; an unreferenced legacy revision needs no alias. The runtime returns the legacy value
while the lecture's local revision still equals the recorded one, so everything that is
current at deploy stays current; once the lecture's own inputs change, it is stale.

The legacy formula lives only here. Existing aliases are never rewritten (a re-run would
bind the alias to a later legacy value). Dry run by default; read-only unless ``apply``.
"""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

from pydantic import ValidationError

from lecturepilot.core.durable_files import atomic_write_json
from lecturepilot.core.models import CourseWorkspaceResult
from lecturepilot.core.storage_layout import StorageLayout, StorageLayoutError
from lecturepilot.sources.course_source_routing import read_source_routing
from lecturepilot.sources.lecture_source_manifest import read_lecture_source_manifest
from lecturepilot.sources.lecture_source_revision import local_lecture_source_revision
from lecturepilot.sources.source_index_models import CourseSourceIndex


def migrate(storage_root: Path, *, apply: bool = False) -> dict:
    report: dict = {"apply": apply, "aliased": [], "unbound": 0, "existing": 0, "skipped": []}
    report["invalid"] = []
    pending: dict[Path, list[tuple[str, Path, str, str]]] = {}
    manifests = storage_root.glob("courses/*/*/builder/source-manifests/*.json")
    for path in sorted(p for p in manifests if not p.name.endswith(".alias.json")):
        name = str(path.relative_to(storage_root))
        try:
            layout, course_id, lecture_id = _identity(storage_root, path)
            alias_path = layout.lecture_source_alias_path(course_id, lecture_id)
            if alias_path.exists():
                report["existing"] += 1
                continue
            legacy = legacy_lecture_source_revision(
                layout, course_id=course_id, lecture_id=lecture_id
            )
            local = local_lecture_source_revision(
                layout, course_id=course_id, lecture_id=lecture_id
            )
        except (OSError, ValueError, ValidationError, KeyError, StorageLayoutError) as exc:
            report["invalid"].append({"path": name, "reason": str(exc)[:300]})
            continue
        if legacy is None or local is None:
            reason = "no legacy revision" if legacy is None else "no lecture-local sources"
            report["skipped"].append({"path": name, "reason": reason})
            continue
        pending.setdefault(path.parents[2], []).append((name, alias_path, local, legacy))
    for course_root, lectures in pending.items():
        bound = _bound_revisions(course_root, {legacy for *_, legacy in lectures})
        for name, alias_path, local, legacy in lectures:
            if legacy not in bound:
                report["unbound"] += 1  # Nothing stored refers to it: no alias is needed.
                continue
            report["aliased"].append(name)
            if apply:
                atomic_write_json(alias_path, {"local": local, "legacy": legacy})
    return report


def _bound_revisions(course_root: Path, revisions: set[str]) -> set[str]:
    """Return the revisions that a stored approval, draft, publication or job refers to."""
    found: set[str] = set()
    for area in ("builder", "canvas", "canvas-drafts"):
        root = course_root / area
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if path.suffix not in {".json", ".jsonl", ".md", ".yaml"} or not path.is_file():
                continue
            if path.is_symlink() or path.name.endswith(".alias.json"):
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            found.update(revision for revision in revisions - found if revision in text)
            if found == revisions:
                return found
    return found


def _identity(storage_root: Path, path: Path) -> tuple[StorageLayout, str, str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    course_id, lecture_id = payload["course_id"], payload["lecture_id"]
    course_root = path.parents[2]
    layout = StorageLayout(storage_root, tenant_id=course_root.parent.name)
    if layout.lecture_source_manifest_path(course_id, lecture_id) != path:
        raise ValueError("Source manifest identity does not match its path.")
    return layout, course_id, lecture_id


def legacy_lecture_source_revision(
    layout: StorageLayout, *, course_id: str, lecture_id: str
) -> str | None:
    """The revision formula used before lecture-local revisions (migration use only)."""
    manifest = read_lecture_source_manifest(
        layout.lecture_source_manifest_path(course_id, lecture_id), course_id, lecture_id
    )
    if not manifest.files:
        return None
    material = "\n".join(
        f"{item.path}\0{item.sha256}" for item in sorted(manifest.files, key=lambda item: item.path)
    )
    provenance = _course_provenance(layout, course_id)
    if provenance is not None:
        material = f"{material}\n{provenance}"
    return sha256(material.encode()).hexdigest()


def _course_provenance(layout: StorageLayout, course_id: str) -> str | None:
    payload: dict[str, object] = {}
    course_root = layout.course_root(course_id)
    workspace_path = course_root / "builder" / "course-workspace.json"
    if workspace_path.exists():
        workspace = CourseWorkspaceResult.model_validate_json(workspace_path.read_text("utf-8"))
        if workspace.course.id == course_id:
            payload["lectures"] = [
                {
                    "id": lecture.id,
                    "title": lecture.title,
                    "date": lecture.date.isoformat(),
                    "material_path": lecture.material_path,
                }
                for lecture in sorted(workspace.lectures, key=lambda item: item.id)
            ]
    index_path = layout.course_source_index_path(course_id)
    if index_path.exists():
        try:
            index = CourseSourceIndex.model_validate_json(index_path.read_text(encoding="utf-8"))
        except (OSError, ValidationError):
            return None
        payload["source_index"] = [
            {"path": item.path, "kind": item.kind, "sha256": item.sha256}
            for item in sorted(index.files, key=lambda item: item.path)
        ]
    routing = read_source_routing(layout.course_source_routing_path(course_id), course_id)
    if routing is not None:
        payload["routing"] = {
            "confirmed": routing.confirmed,
            "source_revision": routing.source_revision,
            "routes": [
                route.model_dump(mode="json")
                for route in sorted(routing.routes, key=lambda item: item.path)
            ],
        }
    if not payload:
        return None
    current = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return _retained_provenance(course_root, current)


def _retained_provenance(course_root: Path, current: str) -> str:
    # Storage-only cleanup receipts mapped the pruned provenance back to the taught one.
    path = course_root / "builder" / "source-retention-provenance.json"
    if not path.exists():
        return current
    receipt = json.loads(path.read_text())
    if receipt["remaining_digest"] != sha256(current.encode()).hexdigest():
        return current
    return receipt["teaching_provenance"]
