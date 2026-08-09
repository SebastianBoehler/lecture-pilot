# Task 6 Report: Professor learning-design approval gate

## Outcome

Implemented a draft-scoped professor review and approval contract for generated lecture learning
designs.

- Each generated draft now has a deterministic canvas digest and a source revision covering the
  selected lecture files, current source index, semantic routing, and lecture schedule.
- Source resolution and provenance capture share the course lock. Draft commit rechecks the token
  under the same course lock after planning, so a concurrent source/course update cannot bless a
  draft planned from an older source snapshot.
- The stored review contains the complete learning map, editable objective, checkpoint prompt and
  evidence criteria, transfer prompt, review interval, semantic prerequisites, deterministic
  warnings, and explicit approval metadata.
- Owner-professor GET, PUT, and approve routes reject stale digests/revisions, unknown or duplicate
  gate/section ids, duplicate/unknown/self/cyclic prerequisites, and intervals outside 1–365 days.
  Ownership is checked for all three routes. Factual/source quality remains an explicit separate
  concern.
- Regeneration replaces the review artifact with a fresh unapproved version. Saving any change
  clears approval.
- Publication now requires approval of the exact current canvas digest, source revision, and map
  revision while holding course, draft, and published-canvas locks. The exact approved map and its
  approval provenance are committed atomically with canvas and publication metadata.
- The professor-only `learning-design.json` remains draft-scoped and is excluded from learner
  publication snapshots.
- Learner map and analytics reads consume the locked published map without regenerating or writing
  it after the lock is released.
- The professor builder shows a focused per-lecture editor beside the actual learner preview. It
  exposes source references and warnings and blocks continue/publish until all current drafts are
  approved.
- Removed the full-course auto-regenerate-and-republish error path. A publish rejection now remains
  visible and cannot silently replace the professor-approved draft.

## TDD evidence

Initial backend RED established the missing review surface:

```text
pytest -q apps/api/tests/test_learning_design_review_routes.py
3 failed: GET returned 404 and the edit/approval flow was unavailable
```

Focused backend GREEN:

```text
learning-design review routes: 3 passed
generation provenance + review + publication concurrency: 7 passed
authorization + publication + published-map read: 7 passed
```

Additional behavior was driven through isolated RED/GREEN cycles:

```text
generation source mutation: RED did not raise; GREEN rejected the stale generation
publication/course lock: RED concurrent source mutation entered; GREEN mutation waited
approval/course lock: RED concurrent source mutation entered; GREEN mutation waited
published map read: RED rebuilt the default objective; GREEN returned the exact approved map
schedule/routing provenance: RED revisions stayed equal; GREEN revisions changed
draft artifact privacy: RED learning-design.json existed in published canvas; GREEN absent
```

Initial UI RED covered the missing learning-design editor and approval block:

```text
ProfessorCanvasDraftStep: 2 failed, 2 passed
```

Focused UI GREEN and regressions:

```text
5 files passed, 13 tests passed
```

The UI regressions cover per-lecture fetch/save/approve state, approval-gated continuation and
publication, builder integration, retry behavior, and zero draft POSTs after a rejected publish.

## Verification

The API gate used the repository venv and dedicated test database:

```text
PATH=/Users/sebastianboehler/Documents/GitHub/lecture-pilot/.venv/bin:$PATH
LECTUREPILOT_TEST_DATABASE_URL=postgresql://lecturepilot:lecturepilot-test@127.0.0.1:55432/lecturepilot_test_pytest
npm run verify:api

Ruff format/check passed
752 API tests passed
22 compiler tests passed
git diff --check passed
```

Web checks:

```text
Prettier, ESLint with zero warnings, Knip, changelog, and docs checks passed
Task 6 focused tests: 5 files, 13 tests passed
Full Vitest suite serialized: 96 files, 292 tests passed
TypeScript and Vite production build passed
git diff --check passed
```

`npm run verify:web` was also run three times. Its default parallel Vitest phase exposed unrelated,
non-deterministic lazy-route timing failures: first only `App.tutorNavigation`, then only
`App.sessionRestore`, then four existing App/lesson route tests. Each isolated failing test passed,
and the complete suite passed with one worker. No Task 6 test failed. Vite retains its existing
large-main-chunk advisory.

## Size and review notes

- All new and modified Task 6 production modules are at or below 300 lines. The largest are
  `course_canvas_store.py` at 297, `course_canvas_generation.py` at 288, and
  `course_learning_design_store.py` at 283.
- `useProfessorCourseBuilder.ts` shrank by eight lines; the review behavior lives in its own hook
  and component. `App.tsx` was not changed.
- Files already above the soft limit remain pre-existing. No new production file exceeds it.
- The learning plan and progress ledger were not edited.
- No manual browser session was run. The review UI, actual preview iframe binding, approval gate,
  invalidation, and production build are covered by focused integration tests.
- Existing non-failing dependency deprecation warnings remain in API tests.
