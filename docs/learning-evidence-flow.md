# Learning evidence and reviewed teaching languages

The learner canvas shows supported, independent and delayed evidence separately.
These are records of attempts within LecturePilot, not a general mastery score or
proof of learning outside the app.

## Reviewed task bank

Practice designs may include a bounded bank of source-anchored exit and delayed
variants. New AI-owned implementations prepare both stages before review.
Existing fully approved designs and hashes retain their authority; empty new
fields do not rewrite legacy revisions. The bank is private assessment material
and must not enter teaching-generation prompts.

Every pending task has a stable task identity, gate revision and issuance time.
The assessment uses the exact task's criteria. The backend chooses transitions
and records which tasks have already appeared. A supported attempt cannot be
reclassified as independent: another reviewed task is required. When the bank is
exhausted, support remains available and the UI explicitly asks for a new reviewed
task. No replacement task is generated in the learner session.

Bounded numeric checks in task variants verify supplied counts and derived
values using explicit operations. They do not execute arbitrary expressions and
do not replace semantic review of the question, evidence and rubric.

## Focus and help

Independent and delayed attempts replace teaching with a focused canvas task.
Notes, sources, examples, language controls and tutor chat stay closed. Reload
waits for current learner state before exposing teaching.

`POST /courses/{course}/lectures/{lecture}/learner-state/support` accepts the exact
gate, revision, task and issuance time. It records support before returning its
content and the updated state. Stale and repeated requests fail. Learner state
returns categorical goal evidence and missing-evidence descriptions from an
assessed attempt. During focus, rubric feedback and assistance stay hidden.
This does not detect outside help, other devices or previously learned material.

## Teaching languages

Professors can prepare German or English explanations from a published canvas,
review original and translated text together, confirm the language of the
published assessment wording, and explicitly publish the exact reviewed digest. Learners select a current published explanation variant from
the canvas toolbar. Assessments retain the published course wording.

`canvas_language_variants.py` defines the teaching-only text contract. Checkpoint,
quiz, component and math blocks never enter translation. Formula, code, numeric
and link tokens in teaching text are preserved. Backend validation checks exact
ordered text identities and protected tokens; professor review checks meaning.
This does not assert psychometric equivalence between translated assessments.

Private files live in
`builder/language-variants/<lecture>/<de|en>/{draft,published}.json`. Each variant
binds the full canonical publication metadata, including source, practice-design,
learning-intent and map revisions. The professor assessment-language declaration
is bound to this publication too; an undeclared legacy language is shown as
not recorded, never inferred from mutable course setup. Changed publications make old variants
unavailable until regenerated, reviewed and published. Learner overlays remain
private; translated text only replaces matching canonical teaching text.

## Implementation changes and reads

AI-owned teaching repairs record a private exact before/after report and the
recorded reason under
`builder/practice-designs/<lecture>/implementation-changes/<revision>.json`.
Professors inspect it during generation. The report is bound to the current
implementation, source and approved intent; it is not a model-written claim that
the repair succeeded, and it does not replace review of the resulting canvas.

Published snapshot reads still validate the current artifacts on every request.
A local profile measured approximately 0.7 ms for a one-section rehearsal and
1.2 ms for a five-section publication. No additional cache was justified by
those measurements. Authorization and private overlays remain request-specific.
