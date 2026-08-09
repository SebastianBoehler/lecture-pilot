# Task 8 Report: pedagogical QA and evaluation contract

## Outcome

Task 8 closes the planned product phase with a deterministic, private learning-design report bound
to one exact draft, source revision, and learning-map revision.

- The existing `learning-design.json` review remains the single authority. Its strict schema now
  contains the learning map, deterministic report, and optional exact-report approval; no second
  approval or report store was added.
- Reports are built during draft initialization and recomputed during update while the existing
  course-to-draft lock is held. Missing or old reports fail as unavailable; reads never lazily build,
  migrate, or repair them.
- Canonically sorted diagnostics identify concepts without assessment, assessments whose own
  section lacks a source, an aggregate absence of source-backed assessments, quiz-only concepts,
  explicit `worked-example-*` blocks after the first assessment, and initially inferred linear
  prerequisites. Diagnostic IDs and the report revision are stable SHA-256 digests; the report
  digest excludes only `report_revision`.
- The strict non-empty transfer-prompt contract remains intact. Empty and whitespace-only transfer
  prompts are rejected, every valid gateful report has complete transfer coverage, and a map with no
  gates reports transfer coverage as `not_applicable`.
- Approval requires the exact report revision and exact diagnostic-ID set. Duplicate, missing,
  unknown, or stale acknowledgements return 409. The approval persists both values and publication
  revalidates them. The entire private review file remains excluded from publication.
- The professor UI renders coverage, actions, and exact diagnostic coordinates in the dedicated
  133-line `ProfessorLearningDesignReport` component. Approval stays disabled while dirty, saving,
  already approved, or incompletely acknowledged. Acknowledgements reset after save, report
  revision, identity, or stale-operation changes and are described only as acknowledged for the
  exact draft.
- Gate outcome events add only `assistance_before_attempt`, `planned_delay_seconds`, and
  `observed_delay_seconds`, copied from the exact stored coaching-turn event. Existing publication,
  learning-map, gate, attempt-kind, and attempt-index fields remain authoritative.
- Release 0.5.0 is dated 2026-08-09 across the coupled root, web, and API versions. The generated
  changelog, privacy copy, architecture, workspace, security, repository, and agent documentation
  describe the same boundary.

Implementation checkpoint: `245d42d feat(learning-design): add exact-draft evaluation gate`.

## TDD evidence

Focused RED was captured before implementation:

```text
backend pure-report, approval, and event contracts: 7 failed
web report/acknowledgement contracts: 3 failed
privacy wording contract: 1 failed
```

Focused GREEN after the minimum implementation:

```text
report, exact-approval, and gate-event API slice: 7 passed
affected learning-design/publication/analytics API slice: 21 passed
report, draft-step, review-hook, and privacy web slice: 4 files, 16 passed
release-page regression after 0.5.0 coupling: 2 passed
```

The tests use pure report functions or real typed stores, filesystem state, API routes, publication
flow, and PostgreSQL-backed suites. No provider, injected store, simulated publication authority,
or hand-written published artifact was added.

## Verification

The requested base database `lecturepilot_test` was created in the existing isolated container and
both it and `lecturepilot_test_pytest` were migrated to head on `127.0.0.1:55432`. Verification used
the repository `.venv` and those explicit database URLs.

```text
npm run verify:fast: passed
npm run verify:api: 767 API and 22 compiler tests passed
npm run verify:full:
  Ruff format/check passed
  767 API tests passed (6 existing deprecation warnings)
  22 compiler tests passed
  changelog/docs/Prettier/ESLint/Knip passed
  100 web files, 304 tests passed
  TypeScript and Vite production build passed
  git diff --check passed
```

The first broad web run exposed one stale test expectation for the former 0.4.0 latest release. The
test was updated to the generated 0.5.0 contract, passed focused, and the fresh final full run passed.
Vite retains its existing large-main-chunk advisory.

The repository-wide size guard still lists pre-existing oversized modules and catalogs. Every new
Task 8 code, test, and authored-doc file is below 300 lines. The pre-existing shared professor
builder fixture catalog was reduced from 446 to 417 lines by extracting focused fixtures. Added-line
searches found no monkeypatch, mock, fake, stub, sample authority, or fallback implementation.

## Sanitized local browser acceptance

The acceptance used headed Playwright with manually started Vite and FastAPI in development-auth
mode. Storage and material roots were disposable under `/tmp/lecturepilot-task8.Gd9tIh`; provider
keys were unset. The synthetic course `task-8-synthetic` contained only a small generated LaTeX
mechanism/changed-case lesson. It passed through the production importer, source index, typed source
routing, lecture source manifest, real draft store, review, approval, and publication operations.
No private material, provider call, or hand-written publication artifact was used.

Observed professor flow:

1. The actual builder draft iframe and deterministic report loaded with four coverage rows and
   three stable diagnostics with section/assessment/block/prerequisite coordinates.
2. Approval and continuation were disabled before all three boxes were acknowledged.
3. Acknowledging all diagnostics showed the exact-draft acknowledgement and enabled approval;
   approval enabled continuation.
4. Saving the changed objective reset all acknowledgements, removed approval, changed the report
   revision from `bb657c6d...` to `b39a4f12...`, and disabled approval/continuation.
5. Re-acknowledgement and exact-report approval succeeded. The real UI published version 1. The
   persisted approval contains the final report revision and all three canonical diagnostic IDs;
   the published tree contains no `learning-design.json`.

Observed learner flow:

1. The actual published learner lesson loaded version 1 with the seeded quiz enabled.
2. Because the quiz UI intentionally starts tutor coaching after submission, and Task 8 forbids a
   provider call, the real quiz-answer API was submitted from the browser page with the active
   student session and publication version. It returned 200, attempt index 1, correct outcome, and
   the durable explanatory feedback contract.
3. Reloading the actual learner route preserved the selected correct option, disabled both options,
   displayed the checkmark, and retained `Richtig.` feedback.

The final browser console contained zero errors and zero warnings; every application request in the
recorded request list returned 200. API and Vite processes and the named browser session were then
stopped. This was a sanitized local acceptance check, not production E2E, a production deployment,
or a provider-quality test.

## Evaluation and deferred boundary

The evaluation contract makes no efficacy claim and records no completed study, ethics approval, or
production deployment. A possible later separately approved evaluation uses delayed independent
performance on a changed task as primary; first independent performance and supported recovery as
secondary; calibration only if later collected; perceived utility; learner as the analysis unit;
minimum cells of five; preview exclusion; and missing follow-up plus version drift as limitations.

H3/H4 broad cleanup, provider changes, research assignment/export, browser timings, learner text,
and deployment remain deferred. Task 8 introduces none of them.
