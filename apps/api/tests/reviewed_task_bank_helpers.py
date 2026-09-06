from lecturepilot.course_practice_target import PracticeTarget


def with_bank(target):
    anchor = target.baseline_task_anchor.model_dump(mode="json")
    return PracticeTarget.model_validate(
        {
            **target.model_dump(mode="json"),
            "supplemental_tasks": [
                {
                    "id": identifier,
                    "stage": stage,
                    "prompt": prompt,
                    "source_anchor": anchor,
                    "surface_change": "Change the supplied scenario while preserving the evidence operation.",
                }
                for identifier, stage, prompt in (
                    (
                        "fresh-exit",
                        "independent_exit",
                        "Justify a conclusion for the new parallel evidence case.",
                    ),
                    (
                        "fresh-delayed",
                        "delayed_transfer",
                        "Explain a conclusion in a new representation of the evidence.",
                    ),
                )
            ],
        }
    )


def expected_goal_evidence(client, course_id):
    learning_map = client.app.state.canvas_workspace.course_canvas_store.learning_map(
        course_id=course_id,
        lecture_id="lecture-open",
    )
    return [
        {
            "gate_id": gate.id,
            "gate_revision": gate.revision,
            "supported": False,
            "independent": False,
            "delayed": False,
            "missing_evidence_ids": [],
            "missing_evidence": [],
        }
        for gate in learning_map.gates
    ]
