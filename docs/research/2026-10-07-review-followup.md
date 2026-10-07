# Review follow-up, 7 October 2026

Status: implementation and local verification completed following review of
`c007fa7`, `5bb657a`, `222b438`, and `895d56c`. These baseline commits were already
on remote `main`. Git history records publication of this follow-up; deployment
status has not been verified.

## Six blockers

1. Ordinary checkpoints without a reviewed task bank or hint ladder now permit
   an unassisted retry. Persisted false exhaustion is normalized on reload and
   submission. Real hint exhaustion requires a configured, exhausted ladder.
   Passing supported work without a fresh task reports bank exhaustion without
   claiming support exhaustion; it does not create independent evidence.
2. Flattening nullable schemas preserves `null` in enums, including nullable
   constants. Regression tests use a JSON Schema validator on provider output
   contracts, including a plain canvas block.
3. Chat's schema requires a null assessment. Parsing and gate validation also
   reject chat assessments. Only checkpoint-card submissions persist assessments.
4. Unexpected streaming failures emit a safe error event and log the internal
   error. The stream emits blank NDJSON heartbeat lines every 15 seconds. Tutor
   execution has a separate two-minute deadline.
5. Math rejects TeX `^^` character substitution before PDF rendering. This
   supplements the isolated untrusted compiler; it does not replace it.
6. Background exam generation renews its durable lease. Long HTTP requests return
   202; clients poll the same idempotency key. An active healthy job cannot become
   a duplicate after its original lease interval.

## Other confirmed findings

- Exam repair prompts request exactly the rejected questions. Failed final
  question reviews produce zero-point invalid questions without keys or reference
  answers. Passing questions remain unchanged. Global/schema contract failures
  still fail closed, and an exam with no verified questions is rejected.
- Generator instructions treat course and protocol text as untrusted evidence.
  Quote validation rejects single tokens and option-only echoes. Verbatim matching
  and quotation length do not independently prove semantic correctness.
- Source operations use shared locks, validate publication authority once, and
  check authority identity plus exact file checksums thereafter. Learner readers
  can overlap. Hidden maps are excluded without case sensitivity; slow source I/O
  does not consume the regex execution budget.
- Tool arguments are schema-validated before dispatch. Edits require one match.
- Known provider failures remain explicit provider errors. Programming exceptions
  retain their original type. Pre-dispatch budget refusals neither record a paid
  provider request nor mark usage unknown. Actual dispatch with unknown usage
  retains its reservation because a provider charge may have occurred.
- Exams and readiness consume daily quotas without occupying or releasing the
  tutor concurrency slot. Source routing, schedule planning, learning intent and
  practice design now share bounded budgets and deadlines with nested reviewers.
- Scope-review caching excludes repair context while preserving the exact intent,
  evidence, model and review-instruction identity.
- Due reviews are globally ordered by due date; lecture interleaving breaks ties.
  Supported review success schedules fresh independent evidence after a real
  delay. Familiar readiness questions no longer reveal `correct_index`.
- Corrupt readiness progress produces a recovery error without replacing the
  file. A lecture counts as passed only when every current published gate has
  a pass bound to its current revision.
- A different checkpoint cannot replace a pending assessment. Memory consent
  recognizes the reported German commands and rejects the formula question.
- A German injection fixture joins the adversarial benchmark cases. It has not
  been tested against a live provider.

## Evidence and limits

Deterministic regressions exercise actual API retries, chat rejection, background
generation/status/idempotency, renewable leases, shared source reads, publication
changes, tool limits, progress recovery, quota concurrency and provider schemas.

- `verify:api` passed: 1,488 API tests, 22 compiler tests and 17 converter tests.
- `verify:web` passed: 517 web tests and the production build.
- `verify:fast` passed: formatting, lint, documentation links, changelog, Knip and
  whitespace checks. Changed code and new modules remain below 300 lines; the
  existing larger `AGENTS.md` receives only four ownership/contract lines.

Browser verification uses a disposable workspace, synthetic source material and
deterministic assessment/generation fixtures. Provider credentials are disabled.
A wrong checkpoint answer remained retryable after reload and a second answer
passed through the checkpoint card. This verifies application behavior, not
provider grading quality.

The browser generated a 25-question exam through HTTP 202 and status polling,
then opened the completed exam. The saved job had one attempt and one exam.
The verification tab reported no console errors. Existing build chunk-size and
PDF-library deprecation warnings remain.

The durable job record survives process restart, but execution does not. After
process failure, an expired lease can be reclaimed and earlier provider work may
be charged again. Healthy lease renewal is not crash-safe exactly-once execution.
Account deletion has no verified API path; progress reset is the tested removal
mechanism for private audit quotations. Institutional retention and backups remain
outside this code review. A bounded live benchmark and human inspection are still
required before claiming grading quality, performance or learner efficacy.
