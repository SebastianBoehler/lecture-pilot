# Task 7 Report: Learner-level outcome analytics

## Outcome

Replaced professor-facing click and event rates with versioned, learner-level learning evidence.

- Quiz analytics now separate unique learners, first-attempt correctness, and correction after
  feedback. Repeated retries remain raw activity and cannot enlarge the mastery denominator.
- Gate analytics use the single `attempt_kind` contract for independent first pass, supported
  retry, and delayed transfer. This removes the deferred Task 2 dependence on the incompatible
  `independent_transfer_passes` boolean combination.
- Quiz events capture one locked canvas/publication snapshot. Assessed tutor turns capture one
  locked published learning map, publication version, and map revision before the model call, and
  persist that captured context after the turn.
- The strict current event schema is stored in `outcome-events.jsonl`. Required publication, map,
  gate, attempt-kind, and attempt-index fields are validated at the writer and reader boundaries.
  Unversioned records are excluded by construction; no compatibility bucket or migration path was
  added.
- Lecture and course rates aggregate within each learner before combining learners. Publication
  versions and gate revisions remain separate, with current and historical labels.
- Every outcome cell returns evidence type, learner sample size, and availability. Percentages are
  absent below five learners. Option distributions are also absent when the quiz cohort or any
  populated option cell is below five.
- Professor responses expose aggregate evidence only. They contain no learner text, tutor
  messages, gate reasons, exact timestamps, learner rows, or attendance/assistance/status
  cross-tabs. Raw counts are labeled only as activity.
- Professor performance and learning-map views now show evidence type, denominator, availability,
  publication version, gate revision, and coverage. Threshold-derived healthy/watch/attention
  ampels and learning-map colors were removed.
- Professor preview remains excluded from analytics, and existing professor authorization remains
  enforced.

The latest explicit direction superseded the original brief's legacy presentation requirement:
unversioned analytics fail closed and are not presented as a supported historical bucket.

## TDD evidence

Backend RED covered repeated-attempt overcounting, same IDs across publications, gate attempt-kind
separation, small-cell disclosure, republishing during context capture, and private response fields.
The old implementation failed these assertions by using event counts, combining versions, deriving
transfer from incompatible booleans, and returning small-cell breakdowns.

Frontend RED covered missing evidence metadata and the presence of threshold-derived ampels. The
updated component and metric tests cover insufficient data, version labels, denominators, outcome
lanes, and removal of threshold presentation.

Focused final GREEN:

```text
strict publication/outcome/preview/result-boundary API matrix: 28 passed
expanded affected API matrix after strict store configuration: 82 passed
focused professor analytics web matrix: 5 files, 15 tests passed
```

The agent-route simulations that injected tutor providers, stores, workspaces, or observability
recorders were removed. Command persistence is instead tested with a concrete typed
`AgentTurnResult` applied to a genuinely published `CanvasWorkspace`. Publication fixtures use
typed source records and `write_lecture_source_manifest`, then the real draft, current review,
exact revision approval, and publish operations.

## Verification

API verification used the repository virtual environment:

```text
npm run verify:api
Ruff format/check passed
753 API tests passed, 6 existing deprecation warnings
22 compiler tests passed
git diff --check passed
```

Web verification:

```text
changelog, docs, Prettier, ESLint with zero warnings, and Knip passed
full Vitest suite serialized: 97 files, 303 tests passed
TypeScript and Vite production build passed
git diff --check passed
```

The default parallel Vitest run passed 302 of 303 tests and hit the existing session-restore
isolation race. The complete one-worker run passed. Vite retains the existing large-main-chunk
advisory.

Repository fast verification also passed:

```text
npm run verify:fast
```

## Size, privacy, and compatibility audit

- `course_canvas_store.py` is 290 lines after extracting locked publication/context reads to the
  83-line `course_canvas_context.py` module.
- All new Task 7 production and test modules are below 300 lines. Touched files already above the
  soft limit are pre-existing catalogs or test modules; Task 7 did not expand their ownership.
- Added-line and new-file searches found no monkeypatch, mock, fake, stub, legacy, or fallback
  implementation. Existing unaffected tests elsewhere in the repository retain their prior test
  infrastructure.
- Production searches found no `legacy_unversioned`, `legacy_activity_events`, `latest_activity`,
  or threshold-ampeled analytics surface.
- No assignment, randomization, migration, compatibility, or speculative configuration was added.
- The learning plan and progress ledger were not edited.

## Remaining notes

- No manual browser session was run. The professor evidence presentation is covered by component
  tests, the complete serialized web suite, and the production build.
- The current learning-design store exposes exact draft, source, and map revisions but no warning-ID
  acknowledgement or report-revision field. Tests use the complete real approval contract currently
  available; no unsupported authority field was invented.

## Review fix round 1

The review findings were addressed without compatibility behavior or injected test boundaries.

- Lecture headline cells now use the same learner-first reducer as course analytics. Each learner's
  current version-bound assessment outcomes are averaged first, then the unique learner means are
  combined. An adversarial five-learner case gives one learner's ten quizzes the same learner weight
  as each peer's single quiz (`0.02`), and the lecture and course payloads agree.
- Quiz and gate records now require a strict event identity, canonical non-empty identifiers, strict
  positive/non-negative integers, timezone-aware datetimes, and no extra fields. Quiz records also
  carry the learning-map revision captured with the document and publication under the same canvas
  lock. Publication, learning-map, and gate-revision mismatches are always historical and never
  enter current headline cells.
- Quiz outcomes are append-if-absent under the real outcome-log lock. Their identity is derived from
  the persisted server attempt index plus course, lecture, learner, component, publication, and map
  revision. The route ensures the outcome for both new and replayed learner state. A real filesystem
  failure with the outcome path temporarily occupying a directory proves repair-and-retry produces
  one learner attempt and one outcome; repeating a successful request also remains one outcome.
- Lecture and course overview cards consume backend headline cells directly. Overview and
  learning-map surfaces display evidence lane, denominator, availability, publication version,
  learning-map revision, and gate revision where applicable. Insufficient cells retain `n` and no
  percentage.
- The obsolete hand-written legacy-publication test was removed. A published quiz snapshot now
  requires the real learning map and matching publication metadata; no legacy presentation or
  incomplete publication path remains.

Review RED evidence:

```text
backend review contract: 3 failed / 3 tests
  missing lecture headline, missing strict event identity/map binding,
  and repaired replay produced zero outcomes
web review contract: 4 failed / 9 tests
  detail-derived headline rates and missing gate/overview version metadata
```

Review GREEN and full verification:

```text
focused backend review contract: 4 passed
focused analytics/publication matrix: 15 passed
focused retry/terminal-state matrix: 9 passed
focused professor analytics web: 2 files, 9 tests passed
npm run verify:api: 756 API tests and 22 compiler tests passed
npm run verify:web: 97 files, 305 tests, static checks, TypeScript, and Vite build passed
npm run verify:fast: passed
git diff --check: passed
```

The Task 7 added-line audit again found no `monkeypatch`, `mock`, `fake`, `stub`, `legacy`,
`fallback`, or `test double` additions. `analytics.py` is 298 lines; all new review code and tests
remain below 300 lines. The size scan continues to report only pre-existing oversized modules,
catalogs, stylesheets, and older test files.

## Review fix round 2

- Outcome records now validate their full semantics at the typed log boundary. Quiz option indices
  are canonical and unique, authored option IDs are unique, the selected ID and correctness must
  match the indexed option snapshot, first-attempt evidence and correction state must agree, and
  gate/quiz event IDs must equal the server-derived immutable attempt identity. The containing
  course and lecture log path must also match the embedded event.
- The event identity excludes mutable request/result metadata. Replaying one attempt with changed
  attendance returns the original persisted answer and keeps one outcome; changing the selected
  answer is rejected and still cannot append a second outcome.
- Quiz submission requires the positive publication version hydrated with learner lesson state.
  The course canvas store compares it with publication metadata under the same snapshot lock,
  before overlay/state lookup or scoring. A stale request receives the typed
  `stale_quiz_publication` 409 and cannot bind an old attempt ID to a new publication.
- The web contract carries the captured publication version through the canvas renderer and answer
  request. Quiz controls remain locked before hydration; the typed stale response reloads the
  lecture and clears the in-memory attempt ID. No learner data enters professor aggregates.
- The quiz renderer and event-integrity regression suite were extracted into focused modules; all
  new production and test files remain below 300 lines.

Review RED evidence:

```text
backend semantic/publication contract: 8 failed / 8 tests
  forged/inconsistent events counted; wrong log path accepted; stale publication was not typed;
  attempt ID could be rebound after republish
immutable replay contract: 1 failed / 1 test
  changed request attendance appended a second outcome
web publication contract: 2 failed / 2 tests
  learner state and quiz request did not require/carry publication version
```

Focused GREEN evidence:

```text
semantic/publication/retry backend matrix: 26 passed
broader focused backend matrix before the size-only extraction: 48 passed
quiz publication web matrix: 4 files, 15 tests passed
```

Final post-extraction verification passed 767 API tests, 22 compiler tests, and the complete web
suite (98 files, 298 tests). Static web checks, TypeScript, the Vite production build,
`verify:fast`, and `git diff --check` passed. Four obsolete simulated quiz-boundary tests were
removed instead of being adapted to the new publication contract; the replacement contract tests
are pure and the backend coverage uses real stores, publication flow, API routes, locks, and
filesystem failures. The round-two and full Task 7 code/test added-line audits both found zero
prohibited monkeypatch, mock, fake, stub, legacy, fallback, or test-double constructs. The sole
touched file still above 300 lines is `App.canvas.test.tsx`, reduced from its pre-existing 383 lines
to 330 by removal of simulated quiz tests; no oversized production or newly expanded test module
remains.

## Review fix round 3

- The learner canvas endpoint now returns a strict `PublishedCanvasView`: the rendered document,
  positive publication version, and canonical learning-map revision are captured from one locked
  published snapshot. The route no longer performs separate publication-existence and document
  reads.
- Learner materialization receives that captured document directly. A concurrent republish cannot
  relabel a rendered document with newer publication metadata.
- The web app retains the complete published view beside the rendered document. Quiz submissions
  use the rendered view's publication version only; learner lesson state is applied only when its
  version matches the view. A mismatch exposes an explicit reload action and contributes no quiz
  locks, learning-path status, or session goal.
- A typed stale-publication response clears the in-memory attempt identity before reloading the
  page, which refreshes both the canvas and learner state. There is no version guess or
  independently hydrated submission authority.
- The real API race regression renders v1, publishes v2 through the real publication workflow,
  observes v2 learner state, and submits the rendered v1 version. The server returns the typed 409
  and persists neither learner quiz state nor an outcome event. The pure view-state contract proves
  a v1 canvas plus v2 state cannot apply v2 locks or submit with v2 authority.

Review RED evidence:

```text
backend atomic canvas contract: 1 failed / 1 test (response omitted publication context)
web view-state contract: module missing / 3 tests blocked
```

Focused GREEN evidence:

```text
atomic snapshot, stale-submit, and canvas/quiz backend matrix: 27 passed
published-view, rendered-version, hydration, App, and preview web matrix: 22 passed
```

Final verification used the repository virtual environment. `verify:api` passed 768 API tests and
22 compiler tests, plus Ruff formatting/lint and `git diff --check`. `verify:web` passed changelog,
docs, Prettier, ESLint with zero warnings, Knip, 99 Vitest files with 301 tests, TypeScript, and the
Vite production build. `verify:fast` also passed. The existing Vite large-main-chunk advisory
remains. No manual browser session was run.

The round-three added-line audit found zero monkeypatch, mock, fake, stub, legacy, or fallback
constructs. New regressions use the real API/store/publication path and a pure deterministic
view-state contract. All changed production modules other than the pre-existing oversized
`App.tsx` remain below 300 lines; the loading decision, parsing, and reconciliation live in the new
109-line module, leaving `App.tsx` one line shorter than its prior 583-line baseline. The report
remains below the 300-line documentation limit.
