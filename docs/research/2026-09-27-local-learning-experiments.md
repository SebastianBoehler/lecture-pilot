# Local learning-flow experiments

27 September 2026. These are implementation hypotheses, not measured learning gains.
They extend the [evidence audit](2026-09-25-lecturepilot-evidence-audit.md).

## Assessment calibration

`scripts/benchmark_gate_models.py --json` now reports the model's credited and missing
evidence IDs alongside gate status. `scripts/calibrate_gate_assessments.py` compares
these categorical predictions with two independent human ratings and one adjudicated
label per case. It reports false-pass, false-rejection, criterion-disagreement and
human-disagreement case IDs without printing learner answers.

Input labels are JSONL with `case_id`, `rater_id`, `status` (`passed` or
`needs_evidence`) and `evidence_ids` (array of approved criterion IDs). Use
`rater_id: "adjudicated"` for the resolved label. Prediction JSON must be an array
from the benchmark or the same contract with `case_id`, `model`, `actual` and
`evidence_ids`. Example invocation after approved data collection:

```bash
.venv/bin/python scripts/calibrate_gate_assessments.py \
  --predictions /private/predictions.json --labels /private/labels.jsonl
```

No genuine student answers or instructor ratings are included in this repository.
The script cannot establish validity until such labels exist. Reviewers must also
rate feedback actionability and leakage separately; status agreement does not
measure those qualities.

## Learner review plan and calendar

The authenticated queue now returns recent completed delayed reviews in addition
to due and upcoming tasks. The selected course dashboard displays those states.
Its calendar button exports a privacy-minimal `.ics` snapshot of pending gate
reviews: generic title, 15-minute block, hashed event UID, no task text or answer.
Overdue reviews export as a block starting now. The file is one-way and does not
cancel events after completion or revision changes. Google Calendar OAuth and a
cross-course combined schedule are not implemented.

## Two-question checkpoint prototype

A locally ignored demo lecture at `demo-learning-lab/lecture-02` opts into a
two-page checkpoint with `:::checkpoint [sequence] ...` followed by two to five
choice lines. The learner chooses an option, then writes a reason, and both parts
are sent as one answer to the existing gate assessment. The choice is not marked
correct before the explanation. Draft choice, page and explanation survive a
reload in the browser tab, scoped by learner, course, lecture and publication.
Only this opt-in format renders as a sequence; existing approved checkpoints
remain single-answer blocks. The demo's question, rubric and process visual are
author-written temporary content, not professor-approved course material.
Professor authoring, item-specific scoring, fresh-case item two, and a controlled
learning comparison remain future work.

## Feedback and media

After an attempt, the ordinary checkpoint can show up to two missing approved
evidence criteria as a next-step cue. The backend continues hiding them during
focused independent attempts. Existing approved hint levels still control domain
support. The local demo uses one process visual because the action order matters;
no new visual is injected into professor material. Feedback usefulness and
visual effects need instructor review and delayed changed-task outcomes.
