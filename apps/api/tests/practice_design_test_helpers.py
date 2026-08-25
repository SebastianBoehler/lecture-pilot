from types import SimpleNamespace

from lecturepilot.course_practice_design_models import (
    PracticeDesignProposal,
    PracticeEvidenceCriterion,
    PracticeHint,
    PracticeMisconception,
    PracticeTarget,
)


def proposal() -> PracticeDesignProposal:
    return PracticeDesignProposal(
        lecture_title="Practice design",
        objective="Derive the conclusion independently from the cited evidence.",
        targets=[
            PracticeTarget(
                id="derive-conclusion",
                title="Derive a conclusion",
                outcome="Derive a justified conclusion from the given evidence.",
                baseline_task="Use the evidence to derive the conclusion.",
                independent_exit_task="Use a parallel evidence set to derive the conclusion.",
                delayed_transfer_task="Use changed surface details to derive the conclusion.",
                evidence_criteria=[
                    PracticeEvidenceCriterion(
                        id="cite-evidence",
                        description="Cites the relevant evidence.",
                    )
                ],
                misconceptions=[
                    PracticeMisconception(
                        id="ignore-evidence",
                        description="States a conclusion without evidence.",
                        diagnostic_cue="The response omits a source-grounded reason.",
                    )
                ],
                hint_ladder=[PracticeHint(level="prompt", content="Identify the key evidence.")],
                review_after_days=7,
                source_refs=["lecture-01.md"],
            )
        ],
    )


def target(**changes: object) -> PracticeTarget:
    return PracticeTarget(**{**proposal().targets[0].model_dump(), **changes})


def document(task: str) -> SimpleNamespace:
    block = SimpleNamespace(id="practice-derive-conclusion", type="checkpoint", text=task)
    section = SimpleNamespace(source_ref="lecture-01.md", blocks=[block])
    return SimpleNamespace(sections=[section])
