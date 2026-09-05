# Presentation readiness — 4 September 2026

## Verdict

Current code is checked at `8e656e2` plus the small local changes below. This
checkout was fast-forwarded by 53 commits; no commit, push or deployment was
performed. Provider configuration is unchanged. The follow-up rehearsal corrected
four source-wording/reference issues, passed factual review, and published local
lecture version 2 through revision-bound approval. All three practice targets
completed distinct independent tasks in the real browser. Their passes persist,
and seven-day reviews are scheduled (not yet completed). An incomplete answer
and an instruction-only answer did not earn passes. See the
[final rehearsal and latency report](2026-09-04-demo-rehearsal-results.md).

Slide design is now owned by the presenter. Reusable content and measured numbers
are in [presentation facts](2026-09-04-presentation-facts.md), not a styled deck.

## Changes and verification

- Professor mobile navigation exposes all seven stages, with wrapping labels
  and a full-width final publication step. Desktop layout and backend gates
  are unchanged. Checked English/light and German/dark at 390px; final German
  label checked separately after its full-width adjustment. At 320px the stage
  grid also fits, but existing top navigation/text still clips slightly; this
  is not a claim that the whole interface passes at that width.
- Study-tool panels load on first selection. Their state survives switches
  within the same course; changing course remounts its tools. Two practice
  library/source reads are avoided on initial dashboard load. No model call
  was eliminated by this change: those were ordinary API reads.
- Structured API error messages reach the learner UI, and learner-state errors
  are announced as alerts. Server-provided recovery paths are not followed
  automatically. Invalid state is not silently converted or deleted.
- The evaluation contract now describes the current two-stage professor
  approval and exact revision binding, not obsolete diagnostic acknowledgements.
- Research and retrospective distinguish implementation, design hypotheses,
  historical feedback and actual measured evidence.

Tests: 1,158 API + 22 compiler + 17 converter passed; 378 web tests across
121 files passed after changes. Python format/lint, web ESLint, Knip, production
build and `git diff --check` passed. Temporary Postgres migration upgrade,
downgrade/re-upgrade and schema check passed. The disposable test DB was isolated
from demo data and removed after verification; the local demo remains running.

`verify:web` itself stopped at pre-existing formatting issues in untracked
`2026-08-25-mit-ai-education-report.md` and `2026-09-03-etq-ai.md`. They were
preserved; downstream checks were run separately. This is not an all-green
`verify:full` claim. Existing dependency deprecation warnings remain.

## Browser flow audit

### Follow-up fixes

- Explicit checkpoints require a non-null assessment even for incomplete answers.
  The model identifies evidenced rubric criteria; the backend derives the next
  approved task and hint. The redundant provider-authored `next_check` contract
  was removed. Browser verification returned needs-evidence without auto-passing.
- Bound checkpoints use one structured completion on the successful path, not
  the filesystem tool loop. Existing transport retries still apply. Ordinary
  tutoring keeps its typed tools and can require multiple provider requests.
- Practice-review schemas constrain source paths to the actual allowed list,
  preventing block identifiers from being emitted as file paths.
- Canvas schemas now allow the required canonical checkpoint IDs. Sections
  missing or mutating approved tasks cannot be cached as completed; existing
  incomplete cached sections are regenerated. Generic text normalization keeps
  approved wording intact; exact practice-contract validation remains mandatory.
- Target placement follows its outcome citation rather than an arbitrary earlier
  hint citation. This is a structural placement rule, not proof that an outcome
  excerpt sufficiently entails the whole task. Live content review caught weak
  anchors and source/task mismatches; the private demo plan was revised.

The complete private demo course was backed up before authoring changes at
`output/review-2026-09-04/course-backup.3qwxLJ/martius-ml/` and byte-compared.
The incompatible old generation-ownership record was moved to
`output/review-2026-09-04/lecture-01-generation-ownership-legacy.json`; it remains
recoverable. No source bytes or other lectures were changed. Approvals use the
local `professor-demo` account and are demo preparation, **not Georg's approval**.

### Earlier content blocker — resolved in the follow-up rehearsal

The final private plan uses an explicit reinforcement-learning outcome anchor
within the section covering all three settings, a tissue-image baseline with
cancer/no-cancer labels, a distinct digit-classification exit, and the revised
empirical-loss task set. Its eight semantic design checks passed. Nevertheless,
generated teaching prose failed subsequent factual review. The final bounded
repair changed the pathology example into mitosis detection while retaining
cancer/no-cancer labels. Earlier passes also flagged overgeneralization about
clustering and an ambiguous description of prediction inputs.

At this earlier checkpoint, no publication or second learner recovery had been
applied. The follow-up manually corrected the failed candidate, reran source-bound
factual review, used revision-bound learning-design approval, and published it.
Backed-up learner recovery and the complete browser rehearsal then succeeded.
Review was not disabled; these are local demo approvals, not supervisor sign-off.
Private request/response artifacts are retained under
`output/review-2026-09-04/practice-canvas-tissue-repaired.json` and the course's
normal generation-job store. All generation requests from this pass finished.

Current-run screenshots stay in gitignored `output/review-2026-09-04/` because
some contain private professor material. They are not publication assets.

| Step                 | Observation                                                                 | Health / boundary                                           |
| -------------------- | --------------------------------------------------------------------------- | ----------------------------------------------------------- |
| 1. Professor setup   | Small-screen stages were horizontally hidden; now visible together          | Layout improved; no new course generated or published       |
| 2. Learner dashboard | One prominent next study action and distinct study-tool tabs                | Loads without the old invalid-state warning after recovery  |
| 3. Lecture canvas    | Published introduction and original slides load; checkpoints stay in canvas | Learner-state API now returns 200; tutor rehearsal separate |
| 4. Source inspection | Citation opens the file workspace and selected slide preview in-app         | Source navigation verified; not an audit of all assets      |
| 5. Practice tools    | First selection loads the library; tabs remain usable                       | No exam generation, grading or paid provider test           |

Private screenshots in that directory document the professor stages after the
mobile adjustment, the learner dashboard warning, and the lecture recovery
notice. They are intentionally not embedded in repository documentation.

No JavaScript console errors were returned by the browser log check. Pre-recovery
API state-rejection errors were visible. Screenshots do not establish contrast
or WCAG compliance; keyboard and screen-reader coverage is not exhaustive.

## Recovery history (earlier rehearsal)

Account `local-demo`, course `martius-ml`, lecture `lecture-01` contained an old
`tutor-state.json`. Read-only schema validation reported:

- incompatible `schema_version`;
- missing `pending_check.assistance_content` and `pending_check.stage`;
- missing `hint_exposures`.

State path (private):
`.lecturepilot/workspaces/users/bf67c55e1add70240ce7df7e/courses/martius-ml/lectures/lecture-01/tutor-state.json`.

The current backend exposes an authenticated
`POST /courses/martius-ml/lectures/lecture-01/learner-state/recover`.
Its implementation validates current published learning-map bindings, clears
matching-revision gate statuses, and replaces invalid coaching state. It does
not delete source material or notes. This is still a progress-changing action:
back up the exact lecture folder and obtain confirmation before applying it.
Do not invoke the broader workspace Reset as a substitute.

Recovery was authorized and applied on 4 September. The endpoint returned 200,
`coaching_state_reset: true`, and `cleared_gate_ids: []`. A fresh learner-state
GET changed from 409 to 200. Attendance was unchanged; the only changed data file
was `tutor-state.json` (plus a new empty gate lock). Canvas response SHA-256
remained `8d8314cea0cbf43420bf85e33010ea5e739a805a01a9b659fc1c6eaf0f5a7f39`.
The byte-verified, private backup is
`output/review-2026-09-04/lecture-01-backup.Fkr7aT/lecture-01/`.
The warning screenshots above document the pre-recovery state.

The first live checkpoint attempt then exposed a separate persistence bug:
`AssessedAgentTurnInput.model_validate(turn.model_dump())` inserted new default
fields into an otherwise valid older gate, invalidating its original revision.
The local fix preserves nested model field presence with `dict(turn)`; it does
not rewrite published gates or relax their validators. A regression failed at
the exact persistence call before the fix and passed afterward. All 32 focused
analytics, strict-map, streaming and recovery tests passed, including rejection
of tampered gates and missing analytics context. Ruff format/lint passed. The
earlier full-suite counts above precede this additional one-line backend fix.

Live retry reached the configured `openai/gpt-5.6-luna` provider but returned
`Model returned a next check without an assessed pending check.` This was
rejected explicitly rather than accepted as learning evidence. No provider
or model configuration was changed. A full successful learning loop is not
established by recovery or the focused regression tests.

A subsequent corrected checkpoint answer completed successfully and displayed
the actual model, feedback and next check. Learner-state GET remained 200 with
schema 2, pending stage `independent_exit`, and no completed gate statuses. The
older published gate repeats its original prompt for that next check; this is
not changed-form transfer. Existing data was not silently upgraded to newly
authored teaching fields. The initial crash had already persisted coaching state
before analytics failed, so these rehearsal attempts are not clean research data.

After recovery, rerun the recommended lecture, one wrong attempt, one targeted
hint/retry, independent-exit behavior and reload. Inspect source/canvas/gate
revision failures separately; recovery does not promise to fix every old artifact.

## Compute and capacity evidence

The later resource-capped, production-mode session/Postgres benchmark supersedes
the development-auth smoke below for read-service sizing: 30 active clients,
14.63 authenticated reads/s, p95 128 ms, zero errors over 120 s, with API and
Postgres capped at 512 MiB each (1 and 0.5 CPU respectively). See
[the full report](2026-09-04-capacity-measurements.md). This is not measured
AI-tutoring capacity or a full deployment on a rented $5 VPS.

Same installed dependencies and build configuration, before/after this change:

| Build artifact             |      Before |     After |
| -------------------------- | ----------: | --------: |
| Main JS, minified          | 1,319.72 kB | 402.20 kB |
| Main JS, gzip estimate     |   393.95 kB | 121.17 kB |
| Initial CSS, gzip estimate |    37.05 kB |  28.06 kB |

Main-JS gzip estimate fell 69.2%. The 883.64 kB math-rendering chunk is now
deferred, not removed: opening a lesson/exam still needs it. The existing
88.35 kB professor-tour preload remains. These are build artifact sizes, not
measured browser load times or total-session traffic savings. The deferred
math chunk still triggers Vite's size warning.

Local read-only smoke measurement, one warmup then 30 requests per level to
`GET /courses/martius-ml/lectures/lecture-01/canvas`; 53,033-byte responses:

| Concurrent requests |      p50 |      p95 | Requests/s | Non-200 |
| ------------------: | -------: | -------: | ---------: | ------: |
|                   1 |  8.49 ms |  9.13 ms |     116.84 |    0/30 |
|                   5 | 44.83 ms | 48.32 ms |     110.53 |    0/30 |
|                  10 | 87.77 ms | 96.22 ms |     111.27 |    0/30 |

This was localhost, development auth, a single warm lecture, Uvicorn reload
mode, no provider calls and no production session/database path. It does **not**
estimate concurrent students or institutional capacity. No sustained load,
cross-course workload, CPU/RAM envelope or failure-recovery load was tested.

Before a university scale claim, run a bounded staging workload combining
authorized reads, tutor turns and authoring separately. Report p50/p95 latency,
errors, CPU/RAM, provider rate limits, input/output/cached tokens, and cost per
completed learning episode (including retries/reviews). Use existing metadata
spans and provider usage records; do not log prompts or learner answers. Report
authoring cost per course separately from marginal learner cost. Keep source
assets shared, conversion isolated and concurrency bounded. No provider price
or API-availability assumptions were made in this pass.
