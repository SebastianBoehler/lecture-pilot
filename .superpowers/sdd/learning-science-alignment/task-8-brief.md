# Task 8 Brief: Pedagogical QA and Evaluation Contract

## Objective

Complete the learning-science alignment initiative with a deterministic, draft-bound
pedagogical report, explicit professor acknowledgement, privacy-accurate evaluation
documentation, and one real local browser verification. This is the final product phase in
this thread.

Do not broaden this task into Hardening 3/4, provider cleanup, deployment, a research export,
or a human-subject study. Keep the factual model reviewer unchanged and correctness-focused.

## Working assumptions

- Extend the existing Task 6 `learning-design.json` review and approval flow; do not create a
  second review authority.
- Hardening 2's strict published learning map remains authoritative. Missing transfer prompts
  are rejected by that contract; the report measures transfer coverage but must not introduce a
  permissive draft/map fallback to manufacture a missing-transfer warning.
- A warning acknowledgement means only that the professor reviewed and accepted a deterministic
  issue for this exact draft. It is not a claim of pedagogical quality, efficacy, or factual
  correctness.
- Only explicitly marked blocks (stable IDs beginning `worked-example-`) are worked examples.
  Never infer this role from prose, captions, language, or style.

## Deterministic report contract

Add small dedicated model/report modules, not new logic in `course_canvas_store.py`.

The report is computed from the exact normalized draft document and its learning map under the
existing course -> draft lock, stored privately inside `learning-design.json`, recomputed on a
learning-design update, and excluded from the published learner canvas.

Required bindings and summaries:

- `draft_digest`, `source_revision`, `learning_map_revision`, deterministic `report_revision`;
- total concepts and concepts with a gate, quiz, or any assessment;
- gate, quiz, source-backed assessment, and transfer-prompt coverage;
- per-concept section/title, gate IDs, quiz IDs, and source-backed assessment IDs;
- canonically sorted structured diagnostics with stable IDs derived from code plus canonical
  coordinates, not from localized message text.

Required deterministic diagnostics where applicable:

- concept without an assessment;
- assessment whose containing section has no source reference, plus an aggregate warning when no
  source-backed assessment exists;
- quiz-only concept with no open-answer checkpoint;
- explicitly marked worked example after the first checkpoint/quiz in the same section;
- initial linear prerequisite edges that require explicit human acknowledgement.

For lectures with no gates, transfer coverage is `not_applicable`, never a misleading zero-percent
failure. A section source reference is required for local source-backed assessment credit; a generic
document-level source reference is insufficient.

The `report_revision` hashes canonical report content excluding itself. Warning IDs are stable
across message/localization changes. Existing stale review artifacts fail clearly and require draft
regeneration; do not migrate or synthesize reports at read time.

## Approval contract

Extend approval request and stored approval with:

- the exact current `report_revision`;
- `acknowledged_warning_ids`.

Under the existing lock, require set equality with the current diagnostic IDs. Missing, unknown,
duplicate, or stale values return 409. Publication revalidates report revision and acknowledgement
set alongside draft/source/map bindings. Regeneration, a saved map edit, or report revision change
clears approval and browser acknowledgement state.

In the professor UI, split a focused report/acknowledgement component so owned files remain below
300 LOC. Show coverage, actionable warnings, exact section/block/gate references, and one checkbox
per warning. Disable approval while dirty, saving, already approved, or any current warning remains
unacknowledged. Use wording such as “acknowledged for this exact draft”, never “quality passed”.

## Outcome metadata

Audit the current strict outcome event rather than duplicating it. Persist only any missing fields
from this list: gate revision, publication version, attempt kind/index, assistance preceding the
attempt, planned delay, and observed delay. Planned/observed delays must come from the stored
revision-bound delayed review. Do not add assignment/condition labels, browser timing, learner text,
raw exports, or research endpoints.

## Documentation and release surfaces

Add `docs/evaluation-contract.md` and update the relevant current documentation:

- `docs/README.md`, `docs/architecture.md`, `docs/workspaces.md`,
  `docs/tenancy-security.md`, `README.md`, and `AGENTS.md`;
- learner-facing privacy copy and its tests;
- `apps/web/src/productChangelog.json` and generated `CHANGELOG.md`.

The evaluation contract must state:

- primary outcome: delayed independent performance on a changed task;
- secondary outcomes: first independent attempt and supported recovery;
- calibration only if later explicitly collected, and perceived utility;
- learner is the analysis unit; current min-cell threshold remains five;
- missing follow-up is missingness/attrition, never success;
- publication/map drift is reported separately;
- preview activity is excluded;
- a later human study requires separate ethics, consent, retention, and data approval.

Avoid any claim of efficacy, institutional approval, production deployment, or a completed study.
If version/changelog validation requires a new release, use `0.5.0` dated 2026-08-09 and update all
coupled version files before rendering the changelog.

## TDD and verification

Capture focused RED before production edits. Required backend coverage:

- valid deterministic report and stable digest;
- strict missing-transfer rejection/coverage invariant (without weakening the learning map);
- quiz-only report with `not_applicable` transfer and open-answer warning;
- locally source-missing assessment warning;
- worked-example ordering and inferred-prerequisite acknowledgement;
- update/regeneration invalidation;
- approval requires exact report revision and exact warning IDs;
- stale/unknown/missing acknowledgement rejection;
- publication excludes the private report and rejects stale approval;
- non-owner access remains forbidden.

Required web coverage:

- structured summary and actionable warnings;
- approval blocked until every warning is acknowledged;
- request contains exact report revision and warning IDs;
- acknowledgement resets on save, revision change, course/user switch, and stale operation;
- privacy and changelog wording.

Use real stores, filesystem, Postgres/API, and browser boundaries. No monkeypatch, mock, fake, stub,
sample data authority, hand-written publication artifact, direct live write, or fallback. Pure report
and reducer tests are allowed.

Run focused tests, then `verify:fast`, `verify:api`, `verify:web`, and one final `verify:full` against
the isolated migrated database. Run the file-size guard and `git diff --check`.

## Browser acceptance

Use a disposable storage root and sanitized synthetic course content through the real
source -> draft -> review -> approve -> publish path. Do not use private professor material or a
model provider.

Verify in the actual browser:

1. Professor opens the real draft iframe and deterministic report; approval is blocked until all
   warnings are acknowledged; saving an edit invalidates approval and acknowledgements; re-review
   and approval enable continuation.
2. Learner opens the real published lesson, submits the seeded quiz, sees durable feedback/lock,
   reloads, and sees the persisted state.
3. No browser console error or failed application request occurs in those exercised flows.

Record exact local steps/results in `task-8-report.md` and state explicitly that this was local,
sanitized verification, not production E2E.

## Completion

Commit with a conventional subject, leave the worktree clean, update the progress ledger, and
return exact verification evidence plus any genuinely deferred H3/H4 items. Stop after one short
read-only sanity review unless it finds a bounded Critical/Important defect.
