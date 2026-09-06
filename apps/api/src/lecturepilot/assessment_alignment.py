def assessment_alignment_instruction() -> str:
    return (
        "Before accepting any baseline, exit or transfer task, solve it from its stated givens. "
        "Verify every stated count, total, subset, unit and constraint simultaneously, not just "
        "the intended answer in the rubric. Contradictory givens make a task unassessable even "
        "when an intended solution is easy to guess; flag this as critical rubric insufficiency. "
        "Check questions and rubrics together by constructing a valid alternative answer from "
        "the source. If the rubric rejects that answer without a stated constraint, repair the "
        "rubric or clarify the task. 'Choose one' limits the number of submitted choices; it does "
        "not assert a uniquely correct choice. Open design and justification tasks may have several "
        "valid answers: accept source-supported alternatives with sufficient reasoning. Require "
        "uniqueness only when the task actually claims it (for example a single-correct-answer quiz). "
        "Do not turn examples or typical applications into exclusive rules. Keep baseline, exit, "
        "transfer, evidence criteria, misconceptions and hints consistent with this distinction. "
    )
