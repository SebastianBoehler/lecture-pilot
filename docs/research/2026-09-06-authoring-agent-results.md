# Authoring worker comparison — 6 September 2026

## Conclusion

On the same 14 approved GDML lecture snapshots, the new agent completed 13 drafts
versus 5 with the prior planner. It used more model calls. The observed median
time was slightly lower, but this is not a controlled speed or cost win. One
approved assessment stopped that run; it was not silently changed to make the
benchmark pass. The follow-up below tests pre-approval design repair separately.

## Paired canvas-stage run

| Measure                                           | Prior planner | Pydantic AI worker |
| ------------------------------------------------- | ------------: | -----------------: |
| Completed drafts                                  |          5/14 |              13/14 |
| Median elapsed time, including failures           |       97.16 s |            89.93 s |
| Provider requests, including reviews and failures |           221 |                375 |
| Median requests per lecture                       |            16 |               20.5 |
| Known-usage standard-rate cost estimate           |        $0.389 |             $0.431 |
| Failed requests with unavailable billed usage     |             3 |                  3 |

The 13 successful agent jobs recovered from 31 validation failures and performed
67 edits. These counts exclude the unsuccessful lecture's repair activity. They
demonstrate recovery on these cases, not a universal reliability guarantee.

Both engines used `openai/gpt-5.6-luna`, low reasoning, identical saved source and
approved-design snapshots, and concurrency three per benchmark process. The
legacy source tree was frozen before the framework edits. Early development work
overlapped the beginning of the candidate run; the baseline overlapped its tail.
This and provider/cache variability limit causal latency comparisons. This was
one run per lecture, not repeated randomized trials.

Private inputs, generated canvases, native histories, request events and result
JSON are under the gitignored `output/authoring-agent-2026-09-06/` directory. The
paired run is `pass-2/`; subsequent fresh checks are `final-check/`. Never commit
the source snapshots or histories. The paired run preceded the explicit protected
assessment-conflict stop; the later checks exercised that final guard.

## Assessment conflict in the paired run

Lecture 14 asks students to choose exactly one architecture for each scenario,
while the approved criteria prescribe fixed architecture choices. Independent
review repeatedly identified multiple defensible answers for some scenarios.
The authoring agent cannot rewrite an approved checkpoint to satisfy its critic.

The initial agent spent 426 seconds before a provider failure ended this loop.
With the explicit review boundary, a fresh run stopped after 39.41 seconds and
8 requests, reporting the approval conflict. This is a successful safety stop,
**not** a successfully generated draft. That workflow required resolving the rubric
or task constraints, reapprove the design, then regenerate. A critic allegation
alone must not be presented as scientific proof that an assessment is invalid.

## Fresh checks on the initial guard

| Case                         | Outcome                                    |    Time | Requests |
| ---------------------------- | ------------------------------------------ | ------: | -------: |
| GDML lecture 03              | Completed; two validation rounds recovered | 68.80 s |       18 |
| GDML lecture 07              | Completed; two validation rounds recovered | 85.68 s |       17 |
| GDML lecture 14              | Professor review required                  | 39.41 s |        8 |
| Text-only ecology lecture 01 | Completed without repairs                  | 15.56 s |        7 |
| Text-only ecology lecture 02 | Completed without repairs                  | 24.89 s |        7 |

The prior text-only comparison completed lecture 01 in 8.68 seconds (2 requests)
and failed lecture 02 after 51.79 seconds (6 requests). The small text sample
also does not show that agentic execution is inherently faster.

A subsequent real local HTTP generation of ecology lecture 01 returned 200 in
23.89 seconds. Its status reported completion and nonzero authoring metrics.
The new draft rendered in the professor preview; its citation opened the source
inside LecturePilot, and the browser reported no console warnings or errors.
This checks the application endpoint and rendering, not a full new-course UI run.
After aligning the local SDK to OpenAI 2.54.0, ecology lecture 02 also completed
through the real HTTP endpoint: 200 in 25.72 seconds, with saved completion status,
nonzero usage and no validation repairs.

## Follow-up: approval-aware repair and reviewer limits

The initial blanket stop on any `practice-*` critic issue was replaced by a
source-backed checkpoint objection check. Unsupported objections can be
dismissed; missing surrounding teaching is repairable. A verified conflict in
an actually approved task still requires a new design revision and approval.

Unapproved learning plans now use native proposal/review correction loops.
Same-source refresh preserves the objective and every ordered target ID/outcome.
Two live failures informed this change: a reviewer omitted mandatory evidence
for its warning (HTTP 502 in 29.28 seconds), and a fresh proposal reduced the
three-target lecture to one target (HTTP 200 in 28.23 seconds). The latter is
not a successful fix. It motivated the deterministic intent-preservation check.

An intent-preserving refresh took 138.18 seconds and three proposal/review rounds,
repairing the architecture rubric to accept justified source-backed alternatives.
However, developer review found a contradictory numerical baseline already in
the original snapshot. Another low-reasoning pass took 44.53 seconds and missed
it. Medium reasoning plus explicit baseline solutions took 113.22 seconds and
two proposal/review rounds; it repaired a different issue but still missed the
literal contradiction. The critic interpreted the intended counts instead of
checking every sentence. These runs are not clean autonomous completions and do
not establish a quality or latency benefit from increasing reasoning effort.

For the local rehearsal, the developer corrected that baseline, removed a
transfer-specific answer from the shared rubric, and removed answer-revealing
task wording through the normal edit endpoint. All original learning goals were
preserved. The edited plan received a fresh semantic review and explicit
`professor-demo` approval. That is rehearsal authority, not Georg Martius's
approval or publication. The private edited plan is not committed.

With that reviewed design, the real local canvas endpoint returned HTTP 200 in
76.50 seconds, persisted five sections without warnings, and reported completed
status. It recovered from five validation failures with ten edits, without a
manual retry. There were 28 provider calls (15 authoring, 13 quality review),
290,780 input tokens including 215,806 cached, and 10,960 output tokens. Known
standard-rate usage is approximately $0.0325, excluding the preceding plan work,
any cache-write charge and hosting. All 28 calls returned successful usage.
The status object's `authoring_metrics.model_requests` counts the authoring
loop only; the provider-event total includes the independent review calls.
This repaired-input follow-up must not replace the paired run's 13/14 result.
The professor preview rendered the corrected checkpoints and in-app source
viewer with no reported console or math-renderer errors. Four slide fetches
initially reported a browser-level `Failed to fetch`; after a clean reload all
ten slide images loaded. The transient transport cause was not established,
so the first browser load must not be described as flawless.

This evidence supports repair/recovery mechanics, not infallible semantic review.
Professor review remains necessary; valid JSON and agreement between model calls
are not proof of mathematical consistency or learning effectiveness.

## Cost interpretation

The estimates apply standard Luna rates of $0.20/M input tokens, $0.02/M cached
input tokens, and $1.20/M output tokens, as inspected on 6 September. Cache-write
tokens are not separately recorded; their listed $0.25/M rate can increase the
estimate. Failed requests may also be billable without returned usage. These
figures are neither invoices nor a reading of the account balance. See
[official OpenAI pricing](https://developers.openai.com/api/docs/pricing).

The measurement covers **canvas authoring and review only**. It excludes course
upload, extraction, routing, learning-plan creation, images, learner sessions,
hosting and human review. Do not label $0.431 as the cost of creating an entire
course or use it to estimate a semester's student cost without further measures.

The native framework initially reported zero usage for this newly named model.
The adapter now takes raw provider usage into both framework and application
accounting. Earlier development runs with incomplete usage were not used for
these cost estimates. The paid environment used Pydantic AI 1.107.5 and OpenAI
SDK 2.44.0; the repository lock pins OpenAI 2.54.0.

## Verification and limits

The final pinned-SDK API suite passed 1,226 tests, plus 22 isolated compiler tests and 17 document
converter tests. Focused regressions exercise same-session correction, resumed
history after provider failure, duplicate requests, unauthorized file access,
source/design revisions, ownership, cancellation, publication fencing and
unchanged-section preservation. An additional HTTP replay regression ensures
the same protected-design failure continues to return 409 rather than 502.
The web verification passed all 385 tests in 123 files and the production build.
The build retains its large-chunk warning for the math rendering bundle.
An additional fresh-generation recovery test covers two successive provider
failures, repair across both HTTP attempts, and reload-visible repair availability.
The additional rubric-warning repair parameter case passed in the focused suite
after the full suite was collected. New tests also cover preserving goals and
recovering a malformed review without restarting the proposal.

Paid runs covered normalized GDML material and unrelated text-only material.
Parser/converter edge cases are covered deterministically; a new mixed-format
upload-to-publication-to-student paid rehearsal was not completed in this pass.
There was no production deployment, VPS capacity test, or learner-efficacy study.

The next performance target is reducing expensive repeated review/context, with
the same validators and fixed input cases—not weakening approval or evidence
checks to obtain a green counter.
