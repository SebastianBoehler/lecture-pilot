"""Shared requirement for meaningful replacement assessment tasks."""


def task_freshness_instruction() -> str:
    return (
        "Compare every baseline, exit, delayed and supplemental task pair for semantic reuse. "
        "Any task may have been completed with help before another is issued independently. "
        "A new ID, shortened wording, renamed entities or reordered sentences do not make a "
        "fresh task. Require a changed scenario, givens or representation that makes the learner "
        "apply the same approved capability again; the previous worked answer must not be "
        "directly reusable. Reusing the same method is expected: changed numerical givens "
        "requiring a new calculation can be sufficient. Do not demand a harder task or a "
        "different operation merely to establish freshness. Preserve the required rubric, "
        "difficulty and source-backed invariant. "
        "In the answer_leakage review, identify concrete changed givens or reasoning needed for "
        "each supplemental task relative to its nearest sibling. Treat a paraphrase of an "
        "already supported task as critical leakage, even when both tasks are individually correct. "
    )
