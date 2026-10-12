# Authoring agent migration

Status: the local application uses the Pydantic AI authoring worker. Production
deployment and a complete upload-to-student rehearsal remain separate gates.
See [measured results](research/2026-09-06-authoring-agent-results.md).

## Scope and acceptance

Replace canvas authoring and repair orchestration with bounded Pydantic AI workflows.
Preserve source routing, approved practice designs, source/design revision checks,
professor publication approval, learner storage, and the explicit assessment path.

The implementation preserves the existing generation/status endpoints and a
scoped authoring-job interface. Deterministic tests cover repair, restart,
cancellation, duplicate requests, stale revisions, source and learner isolation,
and teaching validation. Provider benchmarks are separate from deterministic CI.

## Ownership

- Pydantic AI owns model calls and structured output, not course authority or teaching policy.
- LecturePilot supplies capability-scoped tools and independent validators.
- Source evidence and approved instructions are read-only. Agent writes go to a
  generation-private draft staging directory, never the published canvas.
- Framework history is private job state, not a replacement learner memory store.
- Hidden exit/transfer tasks remain outside authoring prompts and file tools.
- Existing background jobs, leases and final ownership checks remain authoritative.
- A configuration file or working directory alone is not an OS sandbox. Authoring
  model calls have no tools at all (no file, shell or network tools): each call returns
  one section's Markdown, which the backend validates and writes to its assigned draft.

## Runtime and recovery

`CourseCanvasAuthor` replaces the production planner entry point. `authoring_job` runs a
bounded per-section workflow: one Markdown call per missing section with per-section
deterministic checks (`AuthoringWorkspace.section`), a lecture-level check, ONE critic call
over the whole lecture (`course_canvas_quality.py`; split by section only above
`MAX_QUALITY_PROMPT_CHARS`) and at most one repair per flagged section. Repaired sections are
not reviewed again: each becomes a "repaired once, not re-checked" draft warning, and the
lecture-level deterministic check runs again after repairs. Model calls have no tools.
Approved checkpoints are inserted by the backend, not rewritten by the model. The entire
`practice-` block-id prefix is reserved for these checkpoints. Colliding generated block ids
are renamed lecture-wide. Each section prompt carries only that section's approved target
contracts, objective and planning context.

Call budget for a four-goal, five-section lecture (pinned by `test_authoring_call_budget.py`
and `test_generation_call_budget.py`): goals 2-3 calls (was 2-4), teaching 5-9 (was 5-10),
canvas 6 on the happy path and 11 when every section is flagged (was 10-20 plus a checkpoint
judge per objection). A design conflict adds one teaching repair per named goal and rewrites
only the affected sections plus one critic call (previously a teaching review and a complete
canvas re-run).

The private course builder directory contains:

```text
authoring-jobs/<lecture>/<generation>/
  session.json                 # job identity, completion, metrics and the saved critique
  evidence/*.md                # read-only normalized source sections
  draft/*.md                   # assigned editable sections
  section-inputs.json          # per-section input digest for reuse after a teaching repair
  initial-draft.json           # optional revision-checked repair seed
  session-reference.json       # repair attempts point directly to the original session
authoring-metrics/<lecture>/<generation>.json
```

Drafts include course content; they must stay private and follow course deletion
and retention policy. The status response exposes only `authoring_metrics`. There is no global auto-evolving memory or learner-memory access.

Atomic writes, an exclusive job lock, existing durable generation leases, and
source/design/ownership checks protect resume and final publication. A resumed job keeps
saved sections and only writes missing ones.
Targeted repair uses the same worker and resumes the failed generation's history.
Fresh framework failures with saved state also expose the existing AI repair
action. Successive failed retries retain a direct reference to the original
session rather than losing its files or accumulating reference chains.
`POST .../canvas/draft/cancel` uses the existing actor-scoped idempotency key and
revokes ownership; a remote worker notices lease loss through its heartbeat.

The critique (notes per section and which were repaired) is saved in `session.json`, so a
resumed job finishes its pending repairs without another critic call. Three repeated
identical defects within one worker run stop with an explicit
stalled error, including bounded structural repair details. An explicit retry retains
the draft, native history and cumulative metrics but starts a fresh repeat budget;
it cannot silently approve a draft or disable validation. The critic receives each
approved checkpoint's contract (outcome, task, rubric and exact source anchors with
request-local evidence IDs, never hidden exit/transfer wording) and classifies its own
objections in the same call (`course_canvas_quality_checkpoints.py`): `dismiss`,
`repair_section` (missing explanation, repaired in the canvas) or `design_conflict`. A
checkpoint decision is verified deterministically: it must name an approved checkpoint in its
own section and cite only that checkpoint's evidence IDs; the native client retries otherwise,
and an unverifiable decision never escalates or disappears but stays a section note. A
verified conflict that requires changing a fully professor-protected task/rubric stops with
HTTP 409. AI-owned unpublished implementation instead receives one bounded teaching repair of
the named goals while preserving approved intent; see
[learning intent ownership](learning-intent-ownership.md). That repair reuses the
implementation's existing review. The new implementation's job then reuses every section whose
`section-inputs.json` digest is unchanged and writes only the affected sections; the draft
binds to the new implementation revision. Old sessions without digests regenerate fully.
Further conflicts become draft warnings. Model agreement is still not proof of correctness,
and human approval is not silently overwritten.
There is no claim that structured output guarantees semantic correctness.

## Teaching implementation repair after intent approval

The production implementation step uses `teaching_design_job` before canvas
authoring: one structured call per missing approved goal, validated by
`TeachingDesignWorkspace.write`, then one lecture review and one stateless repair per
flagged goal. Repairs are not reviewed again; findings they addressed are labelled
"Repaired once, not re-checked". The backend binds every approved goal and
target order, preserves fixed tasks, and verifies source and intent revisions before
model calls and saves. Valid sibling targets survive repairs.

Private `builder/implementation-jobs/<lecture>/<identity>/` stores `draft.json`
and `progress.json` (flagged and repaired goals). Identity binds source, intent, model,
starting design, its review and repair context. Interrupted jobs resume saved targets and
pending repairs without another review. Unresolved findings remain warnings.
Publication still requires the exact-draft approval.

Metrics count model requests, review rounds, rejected writes and repairs.

## Learning-plan proposals

The former full-plan proposal (`PracticeDesignPlanner.propose`) and its blocking
review loop with transcript replay are removed. Professors refresh unapproved goals
through the goal proposal (`POST .../intent/proposal?refresh=true`); teaching is
generated afterwards by the bounded `teaching_design_job.py` workflow. The planner
keeps only the independent semantic reviewer that this workflow calls.

Shared assessment guidance distinguishes a requested single answer from a
uniquely correct answer. Review must try a source-supported alternative against
the rubric, not turn typical applications into exclusive rules. Each task's
givens must also be mutually consistent. Rubric and objective-alignment warnings
are repaired automatically; other warnings remain visible for professor judgment.
Critical issues cannot pass approval. Existing
source-revision and concurrent-edit checks fence saving the resulting proposal.
Review also distinguishes supplied task quantities from requested derivations;
a rubric must not demand an unasked computation when the approved outcome and
task treat that quantity as given.
An explicitly refreshed plan invalidates its previous approval and draft binding.
There is no special authority bypass for the `professor-demo` account.

This does not silently move professor approval after canvas creation: generated
plan defects are repaired before the existing design approval step, and final
canvas publication still needs the exact-revision review. Schema retries are
bounded; unavailable providers or unresolved semantic issues remain explicit errors.

OpenAI uses native Responses with provider storage disabled and local history.
Authoring/proposal use low reasoning; independent learning-plan review uses
medium reasoning and states concrete baseline solutions. This is not evidence
of a measured quality improvement: the live reviewer still missed one literal
count contradiction, which required developer correction in the demo design.
Google and OpenRouter adapters exist but were not live-benchmarked here. Existing
provider quotas, per-call timeouts and transport retries remain in force. Canvas authoring has a 15-minute job deadline and a shared budget, including
nested critics: 60 paid requests, 1,000,000 input tokens and 120,000 output tokens.
Exhaustion leaves the last private checkpoint resumable. Teaching implementation
has its own shared limits; provider wait time is inside the request timeout, and
cooldowns are capped at 60 seconds.

## Dependency decision

Pin Pydantic AI slim 1.107.5 for the initial integration. The inspected 2.40.0
OpenAI extra requires OpenAI SDK >=3.8.0, conflicting with this repository's
2.54.0 pin. The compatible release avoids an unrelated provider-wide upgrade.
Use installed source for exact APIs; current online docs also describe newer APIs.
The paired paid measurements used OpenAI SDK 2.44.0. The local SDK was subsequently
aligned to the repository's 2.54.0 pin for final regression and live smoke checks.

The legacy planner and its obsolete-only tests are retired. The authoring
benchmark now exercises the native worker; historical comparison evidence
remains in the measured results document.

## Benchmark protocol

Freeze the current implementation before editing it. Compare fresh jobs over the
same source snapshots, approved practice designs, provider model and settings.
Include GDML, unrelated text-only content, and mixed-format input. Do not count
cached/repaired historical drafts as fresh successes.

Report first-pass and final completion, model requests (including review), tool
calls, validation failures, repair attempts, elapsed time, token usage, and cost
with explicit pricing provenance. Include failures in aggregate results. Separate
source preparation, queue time, provider latency, validation, and persistence.
Verify restart and cancellation without weakening publication rules. Promote the
replacement only after its correctness and isolation checks pass; do not claim
better speed, reliability, learning efficacy, or VPS capacity from framework choice.
