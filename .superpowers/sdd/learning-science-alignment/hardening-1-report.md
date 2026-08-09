# Hardening 1 Report: reviewed publication authority

## Outcome

Learner-visible and assessable canvas state now has one authority: a strict reviewed publication
snapshot merged in memory with current `canvas/student/*.md` learner sections.

- Current and historical compiled learner JSON are neither rendered nor scored. No learner
  compiled cache is written.
- A published snapshot requires Markdown, strict typed publication metadata, and a strict typed
  learning map under one read lock. IDs, document digest, and map revision must match.
- Missing, malformed, extra-field, coercible, or mismatched publication artifacts fail at the
  shared learner, quiz, tutor, review, and professor-analytics boundary.
- `CourseCanvasStore.write` and `CanvasWorkspace.write_course_canvas` are gone. Draft writes require
  a captured source revision and always initialize learning design. Publication requires the exact
  current draft, review, approval, map revision, and atomic replacement.
- Quiz, learner-state, practice-exam, readiness, analytics, review-queue, and coaching consumers use
  the same captured publication snapshot. No H1 canvas consumer invents version 1 from absent or
  invalid publication metadata.
- Local and professor preview have no publication exception. Learner tool writes validate a current
  publication and target current learner Markdown only; official evidence remains read-only under
  `/course/canvas`.
- Concurrency coverage uses public operations, real filesystem locks, and thread barriers. No H1
  test patches internal lock or publication functions.

## TDD evidence

Initial RED established six authority failures: compiled overlays were visible/assessable,
publication metadata was untyped, and bare, malformed, incomplete, or mismatched publication
artifacts did not fail consistently. A second RED established the direct-live-write and optional
source-revision bypasses. A preview RED showed local preview omitted the published gate/version.

After the first GREEN, two adversarial type tests found that JSON string values could still be
coerced in publication metadata and learning maps. Both failed across the consumer matrix before
strict validation was enabled, then passed.

Focused final GREEN:

```text
reviewed publication, overlay, quiz snapshot, and real concurrency matrix: 20 passed
complete API pytest before the final strict-type addition: 769 passed
```

Obsolete direct-write, materialization, compiled-cache, migration-reader, and patched-concurrency
tests were deleted or rewritten to use the real typed source -> draft -> deterministic review ->
exact approval -> publish workflow.

## Verification

Verification used the repository `.venv` and a dedicated PostgreSQL 16 container mapped only to
`127.0.0.1:57763`.

```text
alembic upgrade head: passed
alembic check: no new upgrade operations
alembic downgrade base -> upgrade head: passed
npm run verify:api:
  Ruff format/check: passed
  API: 771 passed, 6 existing deprecation warnings
  compiler: 22 passed
  git diff --check: passed
```

Web code and contracts were not changed, so `verify:web` was not rerun for this backend authority
hardening.

## Audit and size

The H1 added-line/runtime audit found no added `monkeypatch`, mock, fake, stub, legacy,
compatibility, or fallback path. The only `write_course_canvas` substring is the required typed
`write_course_canvas_draft` operation; the removed direct-live `write_course_canvas` symbol has no
production or touched-test reference. `legacy_compiled_canvas_path` and `legacy_material_root` also
have no production or touched-test reference.

All H1-created modules and tests are below 300 lines. `agent_tool_executor.py`, already at the soft
limit before H1, is exactly 300 lines after its strict learner-write authorization change. The
repository-wide size guard still reports pre-existing oversized modules and test catalogs; H1 did
not split unrelated ownership while converting their setup to reviewed publication fixtures.

The complete initiative-baseline audit also identifies known later-gate work intentionally left
untouched here: coaching-state payload migrations belong to Hardening 2, while provider/harness
doubles and demo/runtime cleanup belong to Hardening 4. This report claims H1
canvas/publication/overlay authority only, not branch-wide completion of those later hardening
gates.

## Review fix round 1

Five follow-up review findings are closed:

- Persisted quiz files now use one strict, extra-forbid typed schema. Every nested outcome field,
  real publication version, attempt index, file identity, and timestamp is required. Missing,
  malformed, coercible, or extra data returns a shared 409 and is never skipped, migrated,
  overwritten, or reported as current state.
- Learner components and placement are self-contained in `canvas/student/*.md`: complete component
  JSON is inline and placement is section frontmatter. External learner component files and
  `placement.json` cannot change rendering, order, or scoring; label-only external component
  references fail explicitly, and learner tools cannot write external canvas authority files.
- The same canonical quiz-ID validator now guards merged learner canvas GET and quiz submission.
  Published/learner or learner/learner collisions return the same 409 before rendering, scoring,
  state writes, or analytics.
- Publication `schema_version` accepts only the exact integer `1`; booleans, floats, strings, and
  extra metadata are rejected.
- The six reviewer-listed oversized touched tests were split by ownership without removing their
  assertions. Their final sizes are 229, 274, 280, 293, 283, and 252 lines. The app exception
  handlers and learner Markdown codec were also separated so every H1-touched authored file is at
  or below 300 lines.

Review RED was `16 failed, 6 passed`; the focused review GREEN was `22 passed`. Additional strict
component and learner-tool RED tests established the no-unknown and no-external-write boundaries.
The final repository verification used the repository `.venv` and the existing isolated PostgreSQL
16 container on `127.0.0.1:55432`:

```text
npm run verify:api:
  Ruff format/check: passed (477 files)
  API: 794 passed, 6 existing deprecation warnings
  compiler: 22 passed
  git diff --check: passed
```
