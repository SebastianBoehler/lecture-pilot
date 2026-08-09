from __future__ import annotations

from lecturepilot.course_learning_design_models import LearningDesignUpdate
from lecturepilot.learning_map import LearningMap


def apply_learning_design_update(
    current: LearningMap,
    update: LearningDesignUpdate,
) -> LearningMap:
    gate_inputs = {gate.id: gate for gate in update.gates}
    node_inputs = {item.section_id: item for item in update.prerequisites}
    current_gate_ids = {gate.id for gate in current.gates}
    current_node_ids = {node.section_id for node in current.nodes}
    if len(gate_inputs) != len(update.gates) or set(gate_inputs) != current_gate_ids:
        raise ValueError("Learning-design gate IDs must match the current draft.")
    if len(node_inputs) != len(update.prerequisites) or set(node_inputs) != current_node_ids:
        raise ValueError("Learning-design section IDs must match the current draft.")
    graph = {section_id: item.prerequisite_ids for section_id, item in node_inputs.items()}
    _validate_prerequisites(graph, current_node_ids)
    payload = current.model_dump(mode="json", exclude={"revision"})
    payload["objective"] = update.objective
    for gate in payload["gates"]:
        changed = gate_inputs[gate["id"]]
        current_criterion_ids = [item["id"] for item in gate["evidence_criteria"]]
        changed_criterion_ids = [item.id for item in changed.evidence_criteria]
        if len(set(changed_criterion_ids)) != len(changed_criterion_ids) or set(
            changed_criterion_ids
        ) != set(current_criterion_ids):
            raise ValueError("Evidence-criterion IDs must match the current learning-design gate.")
        gate.update(
            prompt=changed.prompt,
            evidence_required=" ".join(item.description for item in changed.evidence_criteria),
            evidence_criteria=[item.model_dump(mode="json") for item in changed.evidence_criteria],
            transfer_prompt=changed.transfer_prompt,
            review_after_days=changed.review_after_days,
        )
    for node in payload["nodes"]:
        node["prerequisites"] = graph[node["section_id"]]
    return LearningMap.model_validate(payload)


def _validate_prerequisites(graph: dict[str, list[str]], valid_ids: set[str]) -> None:
    for section_id, prerequisites in graph.items():
        if len(set(prerequisites)) != len(prerequisites):
            raise ValueError("Prerequisites cannot contain duplicates.")
        if section_id in prerequisites:
            raise ValueError("A section cannot be its own prerequisite.")
        if not set(prerequisites) <= valid_ids:
            raise ValueError("Prerequisites must reference current draft sections.")
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(section_id: str) -> None:
        if section_id in visiting:
            raise ValueError("Prerequisites must not contain a cycle.")
        if section_id in visited:
            return
        visiting.add(section_id)
        for prerequisite in graph[section_id]:
            visit(prerequisite)
        visiting.remove(section_id)
        visited.add(section_id)

    for section_id in graph:
        visit(section_id)
