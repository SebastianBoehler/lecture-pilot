# Claude review remediation, 7 October 2026

Status: local implementation and deterministic integration checks. This is not a
production deployment or evidence of learner efficacy. No paid provider benchmark
was run for these changes. The private review attachment is not copied into Git.

## Implemented

| Phase                     | Changes                                                                                                                                                                                                                                                                                                                                                                                                             | Main ownership                                                              |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| 1: Safety and validity    | Hide future tasks, unselected hints and learning maps; scope sources to current publication and verify file digests; retain newest memory with explicit consent and safe preference keys; fixed multiple-select points; remove TypeError replay; answer every tool call; bound paid requests, tokens, deadlines and cooldowns; move tools off the event loop.                                                       | Tutor context, workspace capabilities, memory, native tutor, shared gateway |
| 2: Efficiency and prompts | Stable context precedes sliding history; static prediction/history/memory rules in system instructions; tutor message and output limits; native schema on every model request; exact scope-review cache; reuse request-local published snapshot and progress; per-section critic cache; concurrent objections; pooled provider clients; incremental history and superseded-read trimming.                           | Model client, turn context, authoring history and reviewers                 |
| 3: Teaching               | Chat checks direct learners to checkpoint cards; isolated grading with answer quotations; readiness uses published approved criteria and grades each open answer separately; improved grader instructions; misconceptions reach authoring; administrative sections avoid filler checks; explicit worked-example ordering; German verbs/labels and adversarial benchmark fixtures; support exhaustion stops retries. | Assessment, readiness, coaching and teaching instructions                   |
| 4: Platform               | Native Pydantic AI model gateway replaces LiteLLM sites; explicit utility/critic tiers; intent-bound refresh uses durable implementation repair; targeted exam repairs preserve passing questions; blind exam solving precedes answer-sheet review; obsolete legacy planner retired; provider schemas derive from validating models; image/tutor/exam/readiness quotas reconcile usage.                             | Native completion, implementation jobs, exam planner and schemas            |
| 5: Review scheduling      | Current independent evidence resets after failure; fresh approved delayed tasks use expanding per-goal intervals; queue interleaves lectures; exams receive bounded source-scoped weak/due goal summaries.                                                                                                                                                                                                          | Coaching goal evidence, review queue and exam focus                         |

Exact source access fails closed when publication, confirmed routing or manifest
identity changes. Reads also verify the captured SHA-256. A builder draft cannot
expand learner access before a matching publication. Audit quotations stay in
private lecture `assessment-audit.jsonl`, outside tutor file roots, response JSON
and categorical professor analytics. Progress reset deletes these excerpts;
the public privacy guide describes their storage and deletion.

Multiple-select questions use four points independent of answer count. Legacy
immutable storage stays intact; student, PDF and solution projections use the same
point rule. Practice submissions remain ungraded. Their history never passes gates.

Unknown or failed provider usage retains the quota reservation. Successful known
usage reconciles actual totals across model/schema calls. Failed image generation
refunds the image count. Job limits include nested paid retries and reviewers.

## Deliberate limits and remaining work

- Readiness now uses approved criteria, but still displays familiar published
  tasks. A hidden-bank readiness mode needs separate issuance/exposure ownership;
  it must not silently consume independent checkpoint or delayed-review tasks.
- Expanding intervals stop when fresh approved tasks run out. The schedule is
  deterministic and bank-aware; it is not a fitted forgetting model or FSRS.
- Practice history is lecture-scoped and bounded in model context, but still scans
  stored exam/attempt files. A revision-aware private index needs separate deletion
  and invalidation coverage before replacing that scan.
- Image HTTP remains synchronous inside a worker thread. The event loop stays
  available, but native async cancellation of that HTTP client remains separate.
- Pydantic AI 1.107.5 and OpenAI 2.54.0 remain pinned. A 2.x framework upgrade needs
  a distinct provider compatibility pass; removal of LiteLLM alone is not that pass.
- Native tutor/provider quality, changed grading strictness, comparative latency,
  cost and learning outcomes require live bounded benchmarks and human review.
  Deterministic tests do not establish those results.

## Next design: unseen readiness tasks

Use a revision-bound readiness issuance record with task ID, purpose, issuance
and prior exposure. Select from a reviewed readiness-specific bank, or atomically
reserve an approved task for that purpose before revealing it. Keep fixed approved
questions and source identities unchanged. Never label an exposed question as
unfamiliar. Persist assistance before displaying support and report exhaustion
explicitly. Assess the answer against exact approved criteria and source evidence;
keep grading separate from tutoring and return source-backed feedback only after
submission. Add exposure, reload, stale publication, deletion and concurrent
checkpoint/readiness regressions before enabling the mode.

## Verification

- `verify:full` passed: 1,444 API tests, 22 compiler tests, 17 converter tests
  and 516 web tests, including private-audit reset and bilingual privacy checks.
  The production build, formatting, ESLint, Knip, changelog and local documentation
  links also passed.
- `verify:fast` passed; the final diff has no whitespace errors. New or expanded
  API modules and tests stay below 300 lines.
- The browser loaded a disposable published lecture and showed an exhausted
  checkpoint with both answer and submission disabled. The actual exam API and
  browser showed fixed four-point questions; exact, wrong and incomplete sets
  scored 4, -1 and 0 after a private saved submission. No provider was called.
- The browser console had transient module-load errors during the deliberate Vite
  restart. The subsequent loaded checkpoint and exam workflows produced no new
  console errors. Existing build chunk-size and PDF-library deprecation warnings
  remain; these checks are not a production capacity or provider-quality test.

Browser fixtures use a disposable local workspace with provider credentials
explicitly disabled. Source material and learner records remain private and
uncommitted. Publication is recorded in Git history. No production deployment
was performed.
