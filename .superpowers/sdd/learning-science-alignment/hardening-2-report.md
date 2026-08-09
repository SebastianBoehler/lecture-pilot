# Hardening 2 Report: strict learning-state contracts

## Outcome

Published learning maps, coaching episodes, learner gate state, delayed reviews, and provider
results now use complete strict contracts.

- Published maps require an objective, unique node/section/gate IDs, explicit prompts, unique
  evidence criteria, transfer prompts, positive review intervals, and exact gate/map digests.
  Persisted reads validate without deriving or repairing fields; `evidence_required` is removed.
- Coaching state requires schema and lecture identity, aware timestamps, exact gate revisions,
  revision-keyed counters, and one authoritative `attempt_kind`. Obsolete payloads and corrupt JSON
  raise typed errors without mutation or blank-state recovery.
- Delayed reviews are keyed by gate and revision and retain their section, transfer prompt,
  scheduled/due timestamps, planned delay, and observed delay. A republished gate cannot overwrite
  or silently hide an older review; invalid published references return an explicit 409.
- Learner gate files require a strict envelope and complete revision-bound decisions. Invalid
  records are not skipped.
- Provider output is one extra-forbid object with nullable `assessment` and separate `next_check`.
  Assessments require an exact persisted pending check; unknown evidence, gate/revision mismatch,
  missing commands, assistance/prompt mismatch, extra fields, fenced JSON, and malformed JSON fail.
  No focus, assessment, evidence, prompt, assistance, or `not_assessed` result is synthesized.
- The streaming route preflights the published canvas, tutor state, and gate state before creating a
  `StreamingResponse`, so corrupt persisted state returns a sanitized JSON 409 rather than an
  aborted 200 stream.
- The hardcoded local-preview tutor and redundant `record_gate` tool authority are removed. Local
  preview now crosses the normal provider readiness boundary. Initiative fake provider,
  completion, history, gate, and harness CI suites invalidated by this boundary were deleted.
- Web learning-map and learner-state types no longer expose `evidence_required`, nullable gate
  revisions, or `not_assessed`.

## TDD evidence

Initial RED established incomplete map acceptance, permissive provider parsing/repair, coaching and
gate-state migration/reset behavior, revisionless attempts, overwritten delayed reviews, and
streaming before state validation. The strict model/store/parser RED contained 28 failures. After
the split assessment/next-check contract and revision-bound reducer/store implementation, the
focused GREEN was:

```text
strict map/provider/coaching/gates/review and API slice: 70 passed
analytics/publication/review follow-up slice: 18 passed
```

Obsolete tests expecting migration, blank-on-corruption, revisionless decisions, synthesized
`not_assessed`, permissive provider JSON, fake LiteLLM completions, or fake successful harness turns
were deleted or inverted. Current CI coverage uses pure contracts/reducers or real filesystem,
published-workspace, store, API, and PostgreSQL boundaries.

## Verification

Verification used the repository `.venv` and the existing PostgreSQL service on
`127.0.0.1:55432`. The missing dedicated `lecturepilot_pytest` database was created and migrated to
head before the final run.

```text
npm run verify:api:
  Ruff format/check: passed
  API: 757 passed, 6 deprecation warnings
  compiler: 22 passed
  git diff --check: passed

npm run verify:web:
  changelog/docs/Prettier/ESLint/knip: passed
  Vitest: 99 files, 301 tests passed
  TypeScript/Vite production build: passed
  git diff --check: passed
```

A live provider smoke was not run because neither `OPENAI_API_KEY` nor `GEMINI_API_KEY` was
configured. No fake provider was substituted.

## Audit and size

The touched-runtime audit found no migration, legacy, compatibility, fallback, monkeypatch, mock,
fake, or stub path. The remaining prohibited terms in touched tests are rejection fixtures proving
that obsolete fields and payloads fail. Production and web searches contain no `evidence_required`
contract and no `not_assessed` state value; the provider prompt mentions `not_assessed` only to
forbid fabrication.

All H2-created modules/tests and primary H2-owned files are at or below 300 lines. The only
over-limit touched file is the pre-existing 446-line shared professor-builder fixture catalog,
where H2 mechanically removed one obsolete field for net negative growth. The repository-wide size
guard continues to report other pre-existing oversized files outside H2 ownership.

## Deferred scope

This bounded H2 commit does not claim the later H3/H4 broad cleanup or Task 8 pedagogical
QA/docs/browser work. Gate outcomes and coaching episode metadata remain separate persisted files;
a crash-atomic multi-file transaction boundary is not introduced here. The current path validates
both stores before streaming and never repairs partial state, but a future storage consolidation can
eliminate that remaining cross-file transaction window.

## Sanity-review fixes

The bounded review round closed two strict-boundary gaps:

- Stream preflight now holds one published-canvas snapshot lock while reading learner state and
  verifies the pending check plus every delayed review against that exact gate revision. Missing,
  republished, or contract-mismatched references return the sanitized JSON 409 before the stream.
- Provider canvas sections, blocks, component data, frames, points, steps, and placements now use
  recursively extra-forbid provider DTOs. The advertised provider fields are converted explicitly
  into domain canvas models; domain-only fields such as `practice_exam_eligible` cannot enter through
  provider output.

Focused RED was 4 failures: both stale-state cases returned 200 and both malformed nested payloads
were accepted. The same slice reached 20 passed, and the adjacent parser/store/queue slice reached
38 passed. Final `verify:api` passed Ruff format/check, 761 API tests, 22 compiler tests, and diff
checks with 6 existing deprecation warnings. Web contracts were unchanged, so `verify:web` was not
rerun. The verifier also exposed one test-only stale `_state_url` import left by the original H2
fixture reduction; its three calls now use the existing `STATE_URL` constant (3 focused tests passed).
