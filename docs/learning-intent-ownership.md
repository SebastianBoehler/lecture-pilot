# Learning intent and teaching implementation

New professor courses follow this flow:

```txt
confirm sources -> propose learning goals -> professor approves goals
-> AI develops and repairs practice -> AI authors canvas -> professor reviews and publishes
```

A goal proposal contains source-backed outcomes, stable ordered IDs, reasoning
invariants and planning constraints. It contains no generated questions, rubrics
or hints. The professor reviews the supporting excerpts, edits goals or context,
and approves that intent. Approval does not certify generated task quality.

## Contracts and storage

`course_learning_intent.py` owns the immutable `LearningIntent`, its goals and
approval. `course_practice_target.py` owns generated teaching targets.
`PracticeDesign` schema 2 holds the intent and a versioned implementation;
`targets: []` means teaching has not been generated yet. Schema 1 remains the
fully protected legacy contract, with its original revision hashes unchanged.

The intent revision covers sources, objective, ordered goals, constraints and
explicitly fixed target hashes. Its approval pins that revision. The design
revision additionally covers generated tasks and their supporting detail.
Approving identical content does not change its content hash.

Files stay under the existing private course builder root:

```txt
builder/practice-designs/<lecture>.json
builder/practice-designs/<lecture>/history/<content-hash>.json
builder/authoring-jobs/<lecture>/<generation>/implementations/<design-revision>/
```

Before replacement, the previous complete design and approval are archived
privately. History follows course retention/deletion; it is not learner memory.
An implementation change gets a separate authoring session, so old task wording
cannot silently reenter the new revision through model conversation history.

## Authority and repair

Only professors/course managers may propose, edit, approve or convert intent.
New routes extend `/admin/courses/{course}/lectures/{lecture}/practice-design`:

- `POST /intent/proposal`: source-backed goals through native structured output.
- `PUT /intent`: edit goals/context against current source and design revisions.
- `POST /intent/approve`: approve goals and explicitly selected fixed targets.

The existing full-design routes remain available for legacy reviewed designs.
An existing full approval requires explicit conversion consent. The UI explains
that goals and constraints stay protected while unselected unpublished teaching
may change. Selected tasks/rubrics stay protected in full; published material
and previous approvals are retained. Source revisions still require new review.

The generation preflight accepts approved intent even when tasks do not exist.
`course_teaching_implementation.py` then uses the existing native practice planner
and semantic reviewer to produce an implementation. The backend checks exact
intent, fixed task hashes, source excerpts and review structure before saving.
Missing or critical implementation review triggers bounded automatic repair.

A source-checked task conflict during canvas authoring may trigger one repair
and one fresh authoring attempt for AI-owned implementation. Legacy full designs
remain protected. The planner's own schema/semantic retries remain bounded.
Repeated conflicts, unsupported protected goals and unavailable providers fail
explicitly; no task dropping, fabricated source, or default rubric is used.

All implementation commits recheck the source revision, complete expected design
(including approval), and worker ownership under the course lock. Cancellation,
source edits and competing professor updates invalidate an in-flight repair.
A model's agreement cannot override any of those checks.

## Publication and learners

Draft binding pins source, learning-intent and implementation revisions. Final
professor approval also pins the exact canvas, learning map and diagnostic report.
Publication metadata retains the intent revision; published readers verify its
binding. A changed draft or intent cannot inherit an older publication approval.

The backend still inserts exact checkpoint text. Canvas authors never receive
hidden exit/transfer tasks through the intent contract. Learner assessments keep
their exact task/rubric revision and the backend chooses the next approved check.
Updating an unpublished implementation does not rewrite a published canvas or
reinterpret old learner answers.

## Verification boundaries

Deterministic tests cover goal-only proposals, explicit conversion, protected
intent and fixed task enforcement, goal edits, revision races, cancellation and
publication binding. Provider output validity and passing critic reviews do not
establish teaching correctness or learner efficacy. Replays must report all
attempts, repair costs and instructor intervention against the same goal set.
