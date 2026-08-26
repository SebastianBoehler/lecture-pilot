# Practice Design Authoring Before Canvas Generation

Date: 2026-08-26

## Purpose

Add a professor-approved practice design between confirmed source routing and
canvas generation. The generated canvas must implement an exact, current
practice-design revision rather than inventing its learning objective and
assessments after generation.

This is the first independently testable slice of LecturePilot's larger
self-regulated-learning architecture. It establishes educational intent and
authority before later work adds learner practice episodes, confidence
calibration, independent exit states, and task-level AI-policy enforcement.

## Product outcome

A professor can review and approve a compact, source-grounded proposal for one
lecture in approximately 5–10 minutes. LecturePilot then generates, validates,
and publishes a canvas only against that exact proposal.

The authority boundary is:

- The professor owns sources, outcomes, expected evidence, task design,
  permissible scaffolds, review timing, and approval.
- The model proposes and implements a design but cannot approve it, weaken it,
  replace its tasks, or silently carry approval across revisions.

## Scope

This slice includes:

1. A typed, revisioned `PracticeDesign` with three to six `PracticeTarget`
   entries for a lecture.
2. Source-grounded model proposal, professor editing, and professor approval.
3. A professor-builder step between source routing and canvas generation.
4. Hard blocking of canvas generation until the current practice design is
   approved.
5. Passing the exact approved design into canvas planning.
6. Deterministic validation that every target is implemented by the generated
   canvas and learning map.
7. Revision binding from source through practice design, draft, learning map,
   learning-design report, and publication.

This slice does not include:

- learner practice-episode state or confidence collection;
- an independent-exit runtime state;
- course-wide or assignment-level AI-policy enforcement;
- learner-facing provenance or professor cohort analytics changes;
- human handoff behavior;
- migration of existing published courses.

Those are subsequent vertical slices. Existing published courses remain
readable. An unpublished legacy draft without a current binding must be
regenerated before publication; there is no compatibility fallback that treats
an inferred post-generation learning map as approved intent.

## Approved workflow

```text
confirmed source routing
  -> generate practice-design proposal
  -> professor edits and approves
  -> generate canvas against exact approved revision
  -> validate target coverage and bindings
  -> professor reviews generated learning design
  -> publish exact bound revisions
```

Canvas generation returns a conflict response when the practice design is
missing, unapproved, or stale. Source changes invalidate the proposal approval.
Practice-design edits invalidate its approval and every dependent draft binding.

## Domain model

### `PracticeDesign`

The course-owned design is stored below
`builder/practice-designs/<lecture-id>.json` and contains:

- `schema_version: 1`
- `course_id`
- `lecture_id`
- `lecture_title`
- `objective`: the lecture-level independent capability synthesized from the
  target outcomes
- `source_revision`
- `targets: list[PracticeTarget]` with 1–8 accepted by the API; the proposal
  prompt requests 3–6 when the source supports them
- `revision`, a canonical SHA-256 digest of every content/provenance field
  except `revision` and `approval`
- `approval: PracticeDesignApproval | null`

The API permits 1–8 targets because thin and unusually dense lectures should
not be padded or truncated to an arbitrary model quota.

### `PracticeTarget`

Each target contains:

- `id`: stable, lecture-local identifier chosen by the proposal and matching
  `^[a-z0-9][a-z0-9-]{0,79}$`
- `title`: short professor-facing label
- `outcome`: observable independent capability, not “understand” or “know”
- `baseline_task`: source-grounded first independent attempt
- `independent_exit_task`: a parallel task intended for the later SRL runtime
- `delayed_transfer_task`: changed surface features with the same target
  reasoning
- `evidence_criteria`: stable IDs and descriptions of required reasoning
- `misconceptions`: stable ID, description, and diagnostic cue
- `hint_ladder`: zero or one entry for each ordered level `prompt`, `cue`,
  `faded_example`, and `worked_step`
- `review_after_days`: integer from 1 through 365
- `source_refs`: one or more exact file paths from the confirmed routed source
  set; page/frame provenance remains on generated canvas blocks

The hint ladder contains approved instructional content, not merely labels.
Levels must be unique and ordered from least to most support. A later runtime
slice will enforce when each level may be revealed.

### `PracticeDesignApproval`

Approval contains:

- `approved_by`
- `approved_at`
- `source_revision`
- `practice_design_revision`

Approval is valid only when both revisions still match current authoritative
state. Editing creates a new design revision and clears approval atomically.

## API and authorization

All routes require the existing course-manager ownership check:

- `GET /admin/courses/{course_id}/lectures/{lecture_id}/practice-design`
- `POST /admin/courses/{course_id}/lectures/{lecture_id}/practice-design/proposal`
- `PUT /admin/courses/{course_id}/lectures/{lecture_id}/practice-design`
- `POST /admin/courses/{course_id}/lectures/{lecture_id}/practice-design/approve`

The proposal endpoint follows the source-routing proposal pattern:

- return the current proposal when source revision matches and `refresh=false`;
- otherwise call the structured-output planner;
- persist only if the source revision still matches after the model call;
- return `409` when sources change during proposal generation;
- return existing provider `502`/`503` errors without mock output.

The update input must carry `source_revision` and `practice_design_revision`.
Stale writes return `409`; invalid contracts return `422`. Approval requires
the current source and design revisions.

## Proposal generation

`PracticeDesignPlanner` receives only the normalized evidence selected by the
confirmed source-routing manifest for the lecture. It uses provider-native
structured output and returns no prose outside the schema.

The prompt requires:

- observable independent outcomes;
- tasks answerable from the cited professor evidence;
- changed exit and transfer tasks that preserve target reasoning;
- evidence criteria precise enough for later gate assessment;
- likely misconceptions supported by the material or clearly phrased as task
  error patterns rather than claims about a learner;
- a progressive hint ladder that never reveals more than its level permits;
- exact source paths from the supplied evidence.

Deterministic validation rejects unknown source paths, duplicate IDs, blank or
identical task variants, unordered hint levels, and unsupported target count.

## Canvas generation and binding

Before a canvas-generation job begins, the API resolves the current approved
practice design under the existing course lock. The job receives an immutable
snapshot, not a path that can be reread opportunistically during generation.

The canvas planner receives the practice design alongside source evidence. It
must:

- organize teaching content around the approved outcomes;
- include one checkpoint for every target using the canonical checkpoint ID
  `practice-<target-id>`;
- use the target's `baseline_task` as the checkpoint task;
- preserve the target evidence-criterion IDs;
- avoid adding assessments that claim to satisfy an unapproved target.

The generated draft stores a `practice-design-binding.json` sidecar containing
the source revision and practice-design revision. Persisting the draft repeats
both revision checks under the course lock. A concurrent source or design edit
fails the generation as stale instead of writing an unbound draft.

Learning-map construction consumes the bound design. It uses the approved
objective, criteria, delayed-transfer task, and review interval instead of the
current generic objective and generic “apply the same reasoning” transfer text.
The learning map records the `practice_target_id` on each gate.

## Validation and publication

Draft validation fails unless:

- every practice target maps to exactly one canonical checkpoint;
- every mapped checkpoint occurs in a source-backed section;
- checkpoint task and criterion IDs match the approved target;
- the learning-map gate carries the approved transfer task and review interval;
- no unknown target ID is claimed;
- the binding revisions match current source and practice design.

The existing learning-design report remains the post-generation implementation
review. Its approval and publication checks gain the practice-design revision.
Professor approval of the generated learning map cannot replace missing
pre-generation practice-design approval.

## Professor experience

The builder adds one step after confirmed source routing:

1. “Generate learning plan” requests the proposal.
2. A compact summary shows target count and source coverage.
3. Each target shows outcome and the three task variants; evidence,
   misconceptions, and hints are collapsed by default.
4. The professor can edit all contract content but not stable IDs.
5. Saving recomputes the revision and clears approval.
6. “Approve learning plan” enables canvas generation for that revision.

The UI explains that this approval confirms intended outcomes and practice
design, not the factual correctness of every future generated paragraph.
Source or design changes show a specific stale state and the required next
action. The canvas-generation button remains disabled and the API independently
enforces the same boundary.

## Failure behavior

- Missing or unconfirmed source routing: proposal generation fails with the
  existing source-routing precondition message.
- Missing practice design: canvas generation returns `409` with “Generate and
  approve the lecture learning plan before generating its canvas.”
- Unapproved or stale design: canvas generation returns `409` with a distinct
  review/refresh instruction.
- Invalid provider output: no partial design is persisted.
- Concurrent source/design edit: the stale operation fails without overwriting
  newer state.
- Invalid persisted design or binding: fail closed with an explicit server
  integrity error; do not infer a replacement.

## Verification

Backend tests must cover model validation, deterministic proposal validation,
stale edits, approval invalidation, authorization, provider failure, concurrent
source changes, generation blocking, immutable generation snapshots, binding
checks, target-to-gate coverage, and publication rejection for mismatched
revisions.

Web tests must cover the new builder order, compact editing, save-before-approve,
approval invalidation, stale messaging, generation-button blocking, provider
errors, and German/English copy.

Browser verification must exercise the real professor flow from confirmed
source routing through practice-design approval and canvas generation, including
one stale-revision path and console-error inspection. Existing API and web
verification suites remain required after narrow tests pass.

## Success boundary

This slice succeeds when no new or regenerated canvas can be created or
published without an exact professor-approved practice design, and the
generated learning map demonstrably implements that design. It does not yet
claim improved learner outcomes; that claim requires the later learner-loop
implementation and a delayed independent-transfer study.
