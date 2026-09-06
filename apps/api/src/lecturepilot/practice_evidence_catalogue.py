from __future__ import annotations

from collections.abc import Sequence
from itertools import zip_longest
import json
from typing import Any

from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.course_canvas_prompt import MAX_SOURCE_EVIDENCE_CHARS
from lecturepilot.course_source_ownership import routed_source_owner
from lecturepilot.course_practice_design_validation import PracticeDesignValidationError

EvidenceCatalogue = dict[str, dict[str, str]]
_DIRECT_ANCHORS = (
    "outcome_anchor",
    "target_invariant_anchor",
    "baseline_task_anchor",
    "independent_exit_task_anchor",
    "delayed_transfer_task_anchor",
)


def evidence_catalogue(source: CanvasDocument, allowed_paths: Sequence[str]) -> EvidenceCatalogue:
    """Bound source evidence fairly across sections; IDs are request-local, never stored."""
    sections = []
    for section in source.sections[:80]:
        path = routed_source_owner(section.source_ref, allowed_paths)
        if path is None:
            continue
        values = [
            value
            for block in section.blocks
            for value in (block.text, block.caption, *block.items)
            if value
        ]
        if not values:
            values = [section.title]
        sections.append(
            [
                {"source_path": path, "excerpt": excerpt}
                for value in values
                for excerpt in _excerpts(value)
            ]
        )
    catalogue: EvidenceCatalogue = {}
    seen = set()
    size = 2
    for row in zip_longest(*sections):
        for anchor in row:
            if anchor is None or tuple(anchor.values()) in seen:
                continue
            key = f"e{len(catalogue)}"
            cost = len(json.dumps({key: anchor}, ensure_ascii=False))
            if size + cost > MAX_SOURCE_EVIDENCE_CHARS or len(catalogue) >= 512:
                return catalogue
            catalogue[key] = anchor
            seen.add(tuple(anchor.values()))
            size += cost
    return catalogue


def _excerpts(value: str):
    text = " ".join(value.split())
    while text:
        end = min(1_600, len(text))
        if end < len(text):
            end = text.rfind(" ", 0, end) or end
            if end < 1:
                end = 1_600
        yield text[:end]
        text = text[end:].lstrip()


def catalogue_schema(
    response_format: dict, catalogue: EvidenceCatalogue, *, proposal: bool
) -> dict:
    if not catalogue:
        raise ValueError("No routed textual evidence is available for practice design.")
    schema = response_format["json_schema"]["schema"]
    schema["$defs"]["PracticeSourceAnchor"] = {
        "type": "string",
        "enum": list(catalogue),
        "description": "Exact evidence ID from the supplied catalogue; do not write a quote or path.",
    }
    if proposal:
        target = schema["$defs"]["PracticeTarget"]
        target["properties"].pop("source_refs")
        target["required"].remove("source_refs")
    return response_format


def compact_evidence_anchors(payload: dict, catalogue: EvidenceCatalogue) -> dict:
    """Include validated professor-edited quotes in the request-local catalogue."""
    lookup = {(item["source_path"], item["excerpt"]): key for key, item in catalogue.items()}

    def compact(value: Any):
        if isinstance(value, list):
            return [compact(child) for child in value]
        if not isinstance(value, dict):
            return value
        if set(value) == {"source_path", "excerpt"}:
            pair = (value["source_path"], value["excerpt"])
            if pair not in lookup:
                key = f"e{len(catalogue)}"
                catalogue[key] = dict(value)
                lookup[pair] = key
            return lookup[pair]
        return {key: compact(child) for key, child in value.items()}

    return compact(payload)


def expand_evidence_ids(
    payload: dict,
    catalogue: EvidenceCatalogue,
    *,
    derive_source_refs: bool = False,
) -> dict:
    def anchor(value):
        if not isinstance(value, str) or value not in catalogue:
            raise PracticeDesignValidationError(
                "Provider returned an unknown or inline evidence anchor."
            )
        return dict(catalogue[value])

    def expand(value: Any):
        if isinstance(value, list):
            return [expand(child) for child in value]
        if not isinstance(value, dict):
            return value
        result = {}
        for key, child in value.items():
            if key.endswith("_anchor"):
                result[key] = anchor(child) if child is not None else None
            elif key == "supporting_anchors":
                if not isinstance(child, list):
                    raise PracticeDesignValidationError("Provider evidence anchors must be a list.")
                result[key] = [anchor(item) for item in child]
            else:
                result[key] = expand(child)
        return result

    expanded = expand(payload)
    if derive_source_refs:
        for target in _objects(expanded.get("targets", [])):
            anchors = [target.get(key) for key in _DIRECT_ANCHORS]
            anchors.extend(
                item.get("source_anchor")
                for key in (
                    "evidence_criteria",
                    "misconceptions",
                    "hint_ladder",
                    "supplemental_tasks",
                )
                for item in _objects(target.get(key, []))
            )
            target["source_refs"] = list(
                dict.fromkeys(item["source_path"] for item in anchors if item is not None)
            )
    return expanded


def _objects(value: Any) -> list[dict]:
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise PracticeDesignValidationError("Provider target collections must contain objects.")
    return value
