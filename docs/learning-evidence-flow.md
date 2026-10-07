# Learning evidence and reviewed teaching languages

The learner canvas shows supported, independent and delayed evidence separately.
These are records of attempts within LecturePilot, not a general mastery score or
proof of learning outside the app.

## Learner review dates

Each published gate has an approved `review_after_days`. After a learner passes its
independent exit, the backend records `scheduled_at` and `due_at` under that
learner's revision-bound `tutor-state.json`. The authenticated course review API
shows first attempts only when due and separately lists unfinished reviews due
within seven days. The dashboard can open the lecture for preparation; the
review-opening API still rejects an early attempt. After a successful delayed attempt, a fresh reviewed delayed task schedules the
next interval at twice the previous interval, capped at 60 days or a longer
approved initial interval. A failed
independent review clears current independent/delayed evidence and resets the
next interval to the approved initial interval. Historical attempts remain saved.
The queue interleaves lectures while preserving due order within each lecture.
Completed reviews without fresh tasks and stale-revision reviews do not become
upcoming actions. These dates support return to practice;
they are not a mastery estimate or a personalized optimal spacing claim.

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
exhausted, a successful attempt receives no extra hint and the UI asks for a new
reviewed task. No replacement task is generated in the learner session.

Bounded numeric checks in task variants verify supplied counts and derived
values using explicit operations. They do not execute arbitrary expressions and
do not replace semantic review of the question, evidence and rubric.

## Evidence-targeted support

Approved hints can bind `evidence_ids` to the rubric criteria they directly help
produce. Unknown or duplicate IDs fail validation. The authoring agent proposes
these bindings and the reviewer checks their pedagogical relevance; professors
can inspect and edit them alongside the hint content. Source catalogue IDs remain
separate from these target-local rubric IDs.

After assessment, `coaching_transitions.py` selects the first unexposed hint
matching `missing_evidence_ids`, preserving assistance order among matches. If no
matching hint remains, only unbound general support is eligible. Unrelated bound
hints are never substituted. If no eligible approved hint remains after failure, `support_exhausted` stops
assessment retries. The learner can review teaching and ask the instructor for
reviewed support or a new task. No worked example or replacement hint is invented. Explicit help before assessment retains its
existing first-approved-hint behavior because no current answer has been assessed.

`CoachingTurnEvent` stores the triggering missing evidence and
`selected_support_level`; pending checks and exposures persist the exact content
under the gate revision. Supported success still requires a fresh approved
independent task. No stable learner-ability label is inferred from an error.

Bindings participate in design and gate digests and exact publication validation.
Empty bindings serialize as before, preserving existing approvals and published
revisions. Existing approved designs are not automatically rewritten. New or
explicitly updated implementations acquire bindings through normal review and
publication. Deterministic tests verify selection and persistence; they do not
establish that an intervention improves learning.

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

## Isolated checkpoint and readiness grading

Explicit checkpoint grading receives only the issued task, approved criteria,
bounded canonical section evidence and the JSON-delimited answer. Chat history,
learner memory, first predictions and future task banks are excluded. Each
claimed criterion needs a verbatim answer quotation. The backend verifies that
the quotation exists, then stores it privately in the learner lecture's
`assessment-audit.jsonl` with its task, publication and gate revision. Quotations
do not enter categorical professor analytics or replace deterministic feedback.

Readiness uses visible published checkpoints with their learning-map required
criteria, plus published quizzes. It keeps hidden independent and delayed task
banks reserved for coaching. Each open answer has a separate native grading
context. Request and token budgets, a 180-second evaluation deadline and
reconciled learner quota bound grading cost. Answer length and embedded grading
instructions do not count as evidence. Repeated attempts alone never increase
the support level. Readiness remains practice on familiar tasks, not a claim of
unfamiliar transfer.
