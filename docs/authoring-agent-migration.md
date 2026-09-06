# Authoring agent migration

Status: the local application uses the Pydantic AI authoring worker. Production
deployment and a complete upload-to-student rehearsal remain separate gates.
See [measured results](research/2026-09-06-authoring-agent-results.md).

## Scope and acceptance

Replace canvas authoring and repair orchestration with a Pydantic AI tool loop.
Preserve source routing, approved practice designs, source/design revision checks,
professor publication approval, learner storage, and the explicit assessment path.

The implementation preserves the existing generation/status endpoints and a
scoped authoring-job interface. Deterministic tests cover repair, restart,
cancellation, duplicate requests, stale revisions, source and learner isolation,
and teaching validation. Provider benchmarks are separate from deterministic CI.

## Ownership

- Pydantic AI owns the model/tool loop, not course authority or teaching policy.
- LecturePilot supplies capability-scoped tools and independent validators.
- Source evidence and approved instructions are read-only. Agent writes go to a
  generation-private draft staging directory, never the published canvas.
- Framework history is private job state, not a replacement learner memory store.
- Hidden exit/transfer tasks remain outside authoring prompts and file tools.
- Existing background jobs, leases and final ownership checks remain authoritative.
- A configuration file or working directory alone is not an OS sandbox. This
  worker has typed file tools, no general shell or arbitrary network tools.

## Runtime and recovery

`CourseCanvasAuthor` replaces the production planner entry point. `authoring_job`
uses the framework's native tool loop and typed completion; `authoring_workspace`
enforces paths and compiles Markdown; `authoring_tools` runs structural and
independent semantic checks. Completion cannot bypass these checks. Approved
checkpoints are inserted by the backend, not rewritten by the agent.

The private course builder directory contains:

```text
authoring-jobs/<lecture>/<generation>/
  session.json                 # native message history, identity and metrics
  evidence/*.md                # read-only normalized source sections
  draft/*.md                   # assigned editable sections
  initial-draft.json           # optional revision-checked repair seed
  session-reference.json       # repair attempts point directly to the original session
authoring-metrics/<lecture>/<generation>.json
```

History includes course content; it must stay private and follow course deletion
and retention policy. The status response exposes only `authoring_metrics`, never
the history. There is no global auto-evolving memory or learner-memory access.

Atomic writes, an exclusive job lock, existing durable generation leases, and
source/design/ownership checks protect resume and final publication. Interrupted
tool batches return uncertainty to the model so it reads before replaying edits.
Targeted repair uses the same worker and resumes the failed generation's history.
Fresh framework failures with saved state also expose the existing AI repair
action. Successive failed retries retain a direct reference to the original
session rather than losing its files or accumulating reference chains.
`POST .../canvas/draft/cancel` uses the existing actor-scoped idempotency key and
revokes ownership; a remote worker notices lease loss through its heartbeat.

Unchanged review batches are reused within a run. Changed teaching is reviewed
again. Repeated identical defects stop with an explicit stalled error. A critic
issue against an exact approved checkpoint is checked against its task, rubric,
source and teaching. Unsupported objections are dismissed; missing explanation
is repaired in the canvas. Only a source-checked conflict that requires changing
the approved task/rubric stops with HTTP 409. Model agreement is still not proof
of correctness, and human approval is not silently overwritten.
There is no claim that structured output guarantees semantic correctness.

## Learning-plan self-repair before approval

`PracticeDesignPlanner.propose` now uses a native-schema Pydantic AI session.
Its output validator hydrates exact evidence IDs, checks the contract, and runs
the independent semantic reviewer. Critical issues return to the same proposal
session so it can revise questions, rubrics, variants and hints together before
the plan is offered for approval. The reviewer has its own schema-correction
loop; malformed review output no longer discards an otherwise usable proposal.
The former single-call proposal adapter was removed, not wrapped. Refreshing a
same-source design seeds that design and preserves its exact objective, ordered
target IDs and outcomes. Repair cannot pass by dropping a difficult target.

Shared assessment guidance distinguishes a requested single answer from a
uniquely correct answer. Review must try a source-supported alternative against
the rubric, not turn typical applications into exclusive rules. Each task's
givens must also be mutually consistent. Rubric and objective-alignment warnings
are repaired automatically; other warnings remain visible for professor judgment.
Critical issues cannot pass approval. Existing
source-revision and concurrent-edit checks fence saving the resulting proposal.
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
provider quotas, per-call timeouts and transport retries remain in force. There
is no added total-job deadline or artificial paid-test budget.

## Dependency decision

Pin Pydantic AI slim 1.107.5 for the initial integration. The inspected 2.40.0
OpenAI extra requires OpenAI SDK >=3.8.0, conflicting with this repository's
2.54.0 pin. The compatible release avoids an unrelated provider-wide upgrade.
Use installed source for exact APIs; current online docs also describe newer APIs.
The paired paid measurements used OpenAI SDK 2.44.0. The local SDK was subsequently
aligned to the repository's 2.54.0 pin for final regression and live smoke checks.

The former planner modules remain available to the baseline benchmark and their
regression tests, not the application's authoring path. They can be retired after
the migration evidence is accepted; no second framework surrounds them at runtime.

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
