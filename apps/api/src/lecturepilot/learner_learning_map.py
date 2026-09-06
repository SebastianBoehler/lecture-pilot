"""Navigation-only HTTP projection; private assessment contracts remain unchanged."""

from pydantic import BaseModel, ConfigDict

from lecturepilot.learning_map import LearningMap
from lecturepilot.learning_map_models import LearningMapNode


class LearnerLearningMapGate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    id: str
    concept_id: str
    title: str
    revision: str
    section_id: str


class LearnerLearningMap(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    course_id: str
    lecture_id: str
    title: str
    objective: str
    revision: str
    nodes: list[LearningMapNode]
    gates: list[LearnerLearningMapGate]


def learner_learning_map(learning_map: LearningMap) -> LearnerLearningMap:
    return LearnerLearningMap(
        course_id=learning_map.course_id,
        lecture_id=learning_map.lecture_id,
        title=learning_map.title,
        objective=learning_map.objective,
        revision=learning_map.revision,
        nodes=[node.model_copy(deep=True) for node in learning_map.nodes],
        gates=[
            LearnerLearningMapGate(
                id=gate.id,
                concept_id=gate.concept_id,
                title=gate.title,
                revision=gate.revision,
                section_id=gate.section_id,
            )
            for gate in learning_map.gates
        ],
    )
