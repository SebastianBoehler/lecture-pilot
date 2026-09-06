# Fresh-course rehearsal — 6 September 2026

## Readiness boundary

The prepared Lecture 1 learner demonstration works locally with real OpenAI
calls. **Unattended creation and publication of a complete 14-lecture course
has not passed. Production has not been updated by this rehearsal.**

Testing used the private professor PDF corpus, an isolated filesystem, local
development identities, the real API, and GPT-5.6 Luna. Original course and
learner workspaces were preserved. This is not a real university-login test,
an efficacy study, or Professor Martius's academic approval of generated content.

## What the real-provider run established

| Stage             | Observed result                                                                                                                                            |
| ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Upload and index  | 14 original PDFs accepted and indexed through HTTP; browser file-chooser automation did not complete                                                       |
| Schedule          | 7.682 s; reviewed rehearsal dates, not an official semester-calendar claim                                                                                 |
| Source routing    | 3.615 s; complete PDF-to-lecture assignments reviewed and confirmed                                                                                        |
| Practice designs  | All 14 exist and pass critical review after documented manual corrections                                                                                  |
| Canvas drafts     | Lectures 1, 2 and 4 succeeded; other attempts failed content/contracts, provider calls or the conservative budget guard                                    |
| Publication       | Lecture 1 passed revision-bound local test-role approval and publication                                                                                   |
| Learner episode   | Incomplete response, supported retry, independent exit, then persisted pass; all three HTTP calls succeeded                                                |
| Browser           | Published student preview, injected grading instruction rejected, supported success, changed independent task restored after reopening, old answer cleared |
| Sources and theme | Original slide opened in the in-app file preview; draft inspected in light and dark mode                                                                   |
| Helpers           | Nine real HTTP cases passed across isolated TeX and Office conversion services                                                                             |

The scripted learner responses took **6.185, 5.039 and 5.640 seconds**. Each
required exactly one provider assessment. The supported pass did not mark the
gate mastered; only the subsequent unaided, changed task did. This establishes
state transitions for these samples, not reliable grading across all students.

The browser injection sample produced `needs_evidence`, not a pass. Browser
reopening restored the independent task in the canvas, not merely in chat.
These were professor-owned preview identities, isolated from learner analytics.

Helper checks: valid TeX including `\top` produced a PDF in 5.365 s; malformed
ZIP, path traversal, missing main file and invalid TeX were rejected. Malformed
Office input, Office traversal, macros and a hash mismatch were rejected.
This is not exhaustive TeX compatibility, OCR validation or a full Office corpus.

Nine additional live API checks passed: traversal/hidden/absolute and empty
uploads were rejected, students could neither upload nor publish, empty tutor
input failed validation, unrelated-course access returned 404, and the missing
draft response retained its allowed-origin and exposed repair headers.

Local verification: `verify:full` passed **1,192 API, 22 compiler,
17 converter and 383 web tests**, plus the production frontend build. The final
preview-navigation regression brings the subsequent web suite to **384 tests**.
`verify:fast` passed formatting, lint, documentation/changelog consistency,
dead-code and diff checks. The existing large math-rendering chunk warning
remains; these checks do not replace production verification.

## Fixes justified by observed failures

1. **Evidence selection instead of quotation generation.** Practice-design
   providers select IDs from a bounded catalogue of exact routed source excerpts.
   The backend restores quotations and derives source paths. Unknown IDs and
   malformed collections fail validation. This removes a fragile copying task;
   it does not prove that the selected evidence entails the proposed teaching.
2. **Backend-owned approved checkpoints.** Section output has native exact-one
   cardinality. The backend inserts the approved canonical diagnostics before
   teaching, in their assigned outcome-anchor section. Conflicting content is
   rejected; exact IDs/text no longer rely on model copying.
3. **Scoped repair contracts.** Section repair receives only its own canonical
   targets. Block patches bind section/block IDs and edit count in the provider
   schema, with deterministic duplicate/coverage validation retained.
4. **Cross-section teaching evidence.** Generation, repair and the critic receive
   exact approved source excerpts needed by the tasks, even when those excerpts
   occur later in the lecture. Hidden assessment wording is excluded. Official
   source files are not mutated. Cached sections are revision/version-bound.
5. **Clearer authoring flow.** Media review is explicitly optional and no longer
   gates generation. Missing source proposals say pending. Successful workspace
   refresh clears stale connection errors. Navigation labels wrap without ellipsis.
   Outline navigation accounts for the measured preview-banner height so the
   sticky banner does not hide the selected section heading.
6. **Recoverable browser errors.** CORS covers guard responses; repairability and
   retry headers are exposed. Reading a draft no longer consumes the paid-generation
   rate bucket. Authorization and CSRF checks remain enforced.

The final scoped repair-schema change has deterministic regression coverage;
another paid Lecture 3 repair was not run after the spending guard stopped work.

## Latency interpretation

Lecture 1's initial successful canvas request took 75.536 s, but content inspection
found missing teaching. Subsequent failed repairs are retained in the experiment
record; the final successful repair took **68.731 s**, not the total time to obtain
that lecture from scratch. It used three generation/repair calls (22.37 aggregate
provider seconds) and nine critic calls (46.04 seconds).

Lecture 2 generated successfully in **121.400 s**: seven generation/repair calls
and eight critic calls. Their provider times totalled 116.77 s. Lecture 4's
earlier successful request took **65.973 s**, with five generation calls and four
critic calls. Overlapping provider durations must not be summed as wall time.

Late tests intentionally limited inference to one concurrent call to honor the
remaining conservative spend reservation. This is **not** the production default.
During competing authoring work, two browser tutor calls waited 34.30 s and
18.14 s before 4.12 s and 3.44 s of provider work. These queue observations are
not evidence of a 5-second production SLA.

The useful optimization targets are repeated content repair, critic passes and
shared inference queuing. Do not remove semantic review because JSON validates.
Prepare and publish course material before the live learner demonstration;
present course creation as asynchronous preparation, not an instant live action.

## Remaining limits and demo checklist

- Several plans needed numerical, criterion-coverage and hint-leakage corrections.
  The same-model critic also made arithmetic mistakes. Review is not independent
  mathematical verification, and changed surface wording is not proof of transfer.
- Generated administrative recall and redundant teaching remain polish issues;
  this pass does not establish optimal pedagogy or measurable learning gains.
- Cross-section source quotations are available to authoring/review, while the
  canvas's primary source-range label remains its assigned section. Inspect
  specific citations in the full source rather than assuming that primary range
  lists every supporting page.
- Full browser upload, complete 14-lecture generation, real university login,
  production deployment/restore and an actual low-cost VPS workload remain open.
- Production SSH gateway authentication failed. No production backup, mutation,
  credential change or deployment was attempted without access.
- Use the prepared published Lecture 1 and its source preview for rehearsal.
  Do not run bulk generation during the learner demo. Recheck real production
  login, assets, one incomplete answer, independent exit and reload after deployment.

Private request/response artifacts and the budget ledger remain below the
gitignored `output/overnight-2026-09-06/` directory. No raw course material,
learner answers or provider credentials are part of this report.

Cost scenarios and their limitations are in
[the measured-cost note](2026-09-06-cost-and-latency-scenarios.md).
