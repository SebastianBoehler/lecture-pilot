from types import SimpleNamespace

import pytest

from lecturepilot.learning_design.learning_goal_outcomes import require_operational_outcomes


def _proposal(*outcomes):
    goals = [SimpleNamespace(id=f"g{i}", outcome=text) for i, text in enumerate(outcomes)]
    return SimpleNamespace(goals=goals)


@pytest.mark.parametrize(
    "outcome",
    [
        "Understand transfer functions.",
        "Students should be able to understand volume rendering.",
        "Be familiar with colour maps.",
        "Die Studierenden verstehen Transferfunktionen.",
        "Kennen die Grenzen von Rainbow-Colormaps.",
    ],
)
def test_vague_outcomes_are_returned_for_repair(outcome):
    with pytest.raises(ValueError, match="g1"):
        require_operational_outcomes(_proposal("Explain a transfer function.", outcome))


@pytest.mark.parametrize(
    "outcome",
    [
        "Explain how a transfer function maps intensity to opacity.",
        "Students can compare surface and direct volume rendering.",
        "Die Studierenden können eine Transferfunktion erklären.",
        "Identify misleading axes in a medical visualization.",
        "Knowledge-graph queries: construct one for a given schema.",
    ],
)
def test_operational_outcomes_pass(outcome):
    require_operational_outcomes(_proposal(outcome))
