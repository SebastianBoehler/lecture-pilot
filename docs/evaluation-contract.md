# Evaluation contract

LecturePilot's learning-design report and outcome events make a future,
consented evaluation measurable. They do not establish teaching quality,
learning efficacy, a completed research study, ethics approval, or production
deployment. Version 0.5.0 was validated with synthetic data in an isolated
local environment only.

## Learning-design review boundary

Each private canvas draft has one deterministic learning-design report in its
existing `learning-design.json` review record. The report is bound to the exact
draft digest, source revision, and learning-map revision. It covers gate,
quiz, source-backed assessment, and transfer-prompt presence, and points to
structural diagnostics such as a concept without an assessment or a checkpoint
without section-local source evidence.

A professor must acknowledge every diagnostic for that exact draft before
approval. Saving or changing any bound revision invalidates the acknowledgement.
Acknowledgement is a publication control, not a claim that the design is good,
effective, or suitable for research. The report and acknowledgements remain
private builder state and are excluded from the published learner canvas.

## Outcome contract

Outcome events contain categorical, revision-bound metadata. Quiz events retain
task and option identifiers, attempt order, correctness where a key exists, and
publication/map revisions. Gate events retain gate and map revisions, attempt
kind and index, the assistance level immediately before the attempt, and the
planned and observed delay from the exact stored coaching turn.

The events do not contain learner answer text, tutor messages, experimental
conditions, randomization assignments, browser timings, or a research export.
Professor preview events are excluded. Professor-facing aggregates suppress
cohorts below five unique learners; raw events and learner identifiers are not
professor-visible.

## Future evaluation measures

If a separately approved study is later run, use the learner as the unit of
analysis and keep revision-compatible outcomes distinct. The intended measures
are:

- Primary: delayed independent performance on a changed task, without tutor
  assistance before that attempt.
- Secondary: first independent-attempt performance and successful supported
  recovery after an initial unsuccessful attempt.
- Calibration: confidence compared with performance, only if confidence is
  explicitly collected in a later approved protocol.
- Perceived utility: a separately collected learner-reported measure, not a
  proxy inferred from product activity.

Aggregate reporting requires at least five learners in a compatible cohort.
Publication-version, learning-map, gate-revision, and attempt-kind drift must be
reported separately rather than pooled. Missing or delayed follow-up is
attrition/missingness, never evidence of success; analyses must state the
follow-up window and denominator.

## Study and operations gates

No human-subject study, recruitment, consent flow, research retention schedule,
or institutional ethics/data-protection approval is included here. Those require
a separate protocol and participant notice before collection begins. Likewise,
this contract does not approve a production rollout. Production use still
depends on the security, privacy, retention, recovery, capacity, and operations
gates documented elsewhere in this repository.
