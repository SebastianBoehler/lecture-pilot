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
