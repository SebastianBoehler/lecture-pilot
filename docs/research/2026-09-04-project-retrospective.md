# LecturePilot project retrospective

Prepared 2026-09-04 for the University of Tübingen research-project
presentation. This is a reconstruction from the Git history, local journal,
design-QA records, and the course feedback archive. It is not a human-subject
study record and does not establish educational efficacy.

## The short story

LecturePilot started as a constrained, source-aware course tutor prototype. It
was deliberately pushed away from "chat next to lecture notes" and toward a
professor-controlled learning loop: approve the evidence and task design,
require an attempt, give bounded help, then ask for independent evidence later.
The most important iterations came from testing the actual course workflow and
repairing failures in authority, grounding, assessment integrity, and the
student/professor experience rather than adding more model features.

## Timeline of decisions and evidence

| Period    | Evidence and observed need                                                                                                                                          | What changed                                                                                                                                                                                                                            | What we learned                                                                                                             |
| --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| 5-12 Jun  | Initial prototype commits (`36b190a`, `1b920bc`, `e8e569b`, `ba602c1`)                                                                                              | Added a course-grounded Markdown canvas, typed tutor tools, course planning, professor preview and reviewed publication.                                                                                                                | The course canvas, rather than chat history, needs to be the durable learning surface.                                      |
| 17 Jun    | Professor demo journal: quizzes were sparse, learning checks appeared too late, source slides needed to remain visible, and exam preparation should cross lectures. | Added denser quiz/checkpoint support, original-slide interleaving, typed scaffold policy, and exam-readiness work (`755e150`, `03fcbba`, `8b51ed6`, `69797e3`).                                                                         | A polished explanation is insufficient. Learners need strategically placed opportunities to retrieve, explain, and apply.   |
| 8-14 Jul  | Real university identity and deployment work exposed that browser-provided identity and a casual demo path were not sufficient.                                     | Added signed sessions, Alma-derived roles, owned courses, learner isolation, course scheduling, isolated previews, strict quality gates and deployment controls (`434830d`, `c48ddc2`, `d303403`, `338cca0`, `f98b881`).                | Correct authority and privacy boundaries are product requirements, not deployment polish.                                   |
| 13-20 Jul | Real generation and update flows produced stale requests, interrupted work, LaTeX/PDF failures and recovery cases.                                                  | Added job leases, idempotency, bounded retries, metadata-only traces, Tectonic isolation, source-scoped repair and crash-safe publishing (`a3ec63e`, `cda1800`, `b35b345`, `429a6cb`).                                                  | A university tool must fail clearly and recover predictably; provider calls cannot define the system state.                 |
| 26 Jul    | Softwarequalität live-corpus audit found incorrect answer keys, hallucinated generic quizzes, incomplete coverage, source leakage and formally wrong content.       | Enforced explicit keys and options, source-backed assessment review, filtered-source repair, full re-audit and exact lecture coverage.                                                                                                  | Structural validity and fluent prose do not guarantee correct learning material. Source-bound semantic review is necessary. |
| 31 Jul    | Need for realistic, private exam practice without mixing it into formative tutoring.                                                                                | Added source-grounded practice-exam storage, PDF/solution output and separate review flow (`fcf8ff6`, `ed91696`, `66211cd`, `a03888f`).                                                                                                 | Formative checks and exam simulations serve different pedagogical and data contracts.                                       |
| 9 Aug     | Learning activity had to remain interpretable across edits, assistance levels and delayed follow-up.                                                                | Added durable attempts, revision-bound learning maps, due-review queue, design approval and outcome analytics (`dc0e6fe`, `9c8b1a4`, `717d5db`, `245d42d`).                                                                             | "Completed with help" must never be reported as independent mastery.                                                        |
| 10-26 Aug | Course ingestion and generation needed explicit human control before publication; learning theory needed to govern the generator input.                             | Added source routing, safe document conversion, learning-design diagnostics, then a professor-approved practice-design contract with baseline, exit and delayed-transfer tasks (`6f938e6`, `0cf75e1`, `03fed22`, `fe18d47`, `8e656e2`). | The strongest control point is before generation: define the observable learning outcome and allowable help first.          |

## Feedback to implementation loop

Dates in the table identify the feedback/iteration period, not necessarily the
implementation day. The June 17 requests landed as quiz, slide and readiness
commits on July 2, followed by the scaffold policy on July 3. The final August
26 practice-design work is included in current HEAD `8e656e2`; this checkout was
53 commits behind before a fast-forward on September 4. Historical verification
records below must not be presented as freshly rerun tests.

### Professor demo feedback, 17 June

The journal identifies the speaker only as "professor." The student's account connects
the project to Georg Martius; the note itself is not independent attribution
of named quotations or endorsement.

It records four specific requests:

1. Put multiple-choice checks at meaningful transitions in the canvas.
2. Treat those checks as evidence checkpoints, not decorative content.
3. Offer exam readiness across previously unlocked lectures, including open and
   task-specific work where appropriate.
4. Keep original professor slides present, then add explanations and practice
   around them.

Those requests produced first-class quiz/checkpoint blocks, durable learner
attempts, cross-lecture readiness, interleaved source slides, and later the
practice-design contract. The implementation went further than adding widgets:
quiz and gate attempts bind to publication and learning-map revisions, while
generation requires source evidence and professor approval.

### Lecture feedback archive

The private course archive includes historical lecture feedback and
`ideas_after_feedback2024.txt`. That note flags gaps in probability background
and proposes slide/formula pointers, concept summaries, prerequisite refreshers,
Python support and a mock exam. These are earlier course-design inputs, not
responses to LecturePilot and not a 2026 learner trial.

Do not reuse the draft's survey percentages in slides: item-specific respondent
and selection denominators need checking against the original questionnaire.
In particular, a multiple-selection percentage is not automatically a percentage
of students. The qualitative rationale suffices without an ambiguous statistic.

This is a persuasive design problem, but not a product result. It motivates:

- source-backed worked transitions before asking for a solution;
- small retrieval checks at concept boundaries;
- hints that point to the next reasoning move rather than reveal an answer;
- learner-owned pace and revision support; and
- original slide provenance so a generated explanation stays inspectable.

### Quality-audit feedback

The Softwarequalität audit is a useful negative case. It found that fluent
generated content could still contain wrong formal definitions and answer keys.
The response was not to make the model sound more confident. The pipeline now
uses bounded evidence, deterministic validation, structured review, targeted
repair and a re-audit before persistence. That is the engineering logic behind
the presentation line: model output proposes content, while the surrounding
system retains authority.

## Current architecture as a research instrument

```txt
Professor sources + approved learning design
  -> source routing + private draft generation + deterministic review
  -> explicit professor publication
  -> learner attempt on the canvas
  -> source-grounded, assistance-bounded tutor support
  -> independent exit and later changed-form transfer task
  -> privacy-minimized, revision-bound outcome metadata
```

The contribution is the controllable interface between teaching material,
feedback, learner action and measurement. It makes later comparisons possible
without treating chat volume, engagement or a correct answer after a hint as
proof of learning.

## Engineering choices that support a university deployment

- Same-origin React/Vite web app and FastAPI policy layer; the browser never
  chooses user, course, role or provider authority.
- One shared CPU-hosted application stack with Postgres and a persisted volume;
  no per-learner container and no local foundation-model inference requirement.
- Model/image calls remain behind a backend provider boundary. Cost-sensitive
  high-volume tutoring can use a smaller configured model; stronger models can
  be reserved for bounded authoring/review tasks.
- Uploaded TeX/PDF processing is isolated. Source material, learner overlays,
  course drafts and public canvases have distinct storage/permission roots.
- Analytics exclude raw learner text from professor aggregates and suppress
  cohorts below five. The evaluation contract explicitly defers consent,
  ethics, retention and study approval to a separate protocol.

This lowers local compute and operational footprint. It does not by itself
prove a lower total service cost, privacy compliance, scalability limit or
educational benefit.

## What to present as unfinished

### September 4 rehearsal: contracts are not the same as a working old workspace

Pulling 53 commits exposed stale local tutor and generation-ownership records.
The exact affected data was backed up; recovery was explicit. A separate gate
serialization defect was fixed without rewriting published gate revisions.
An incomplete live answer then exposed redundant model ownership of the next
check: the provider was being asked to reproduce a server-determined transition.
The backend now constructs that transition, and explicit checkpoints use a
single structured assessment path. The real incomplete-answer rehearsal now
returns needs-evidence rather than a contract failure.

Rebuilding the older demonstration uncovered authoring-contract mismatches too:
the strict model schema omitted required checkpoint IDs, completed-section
caches accepted missing approved tasks, and generic normalization rewrote
teacher-approved task text. These now have focused regression coverage. Source
placement follows the outcome anchor, not whichever hint happens to match first.
Live source review still caught weak anchors and a task using an example outside
its section's evidence. Those are reasons to revise the plan, not suppress review.

The current verification passed 1,147 API, 22 compiler, 17 converter and 377 web
tests, plus five capacity-harness tests. Prepared-course authenticated load tests
also demonstrated a small read footprint, with explicit limits on extrapolation.
The [readiness report](2026-09-04-demo-readiness.md) owns publication/rehearsal
status; the [capacity report](2026-09-04-capacity-measurements.md) owns measurements.
This is engineering evidence, not a student-learning result.

1. No learner study, causal efficacy result or ethics approval has been
   completed. The next credible evaluation uses delayed, unaided changed-form
   performance as its primary outcome.
2. September 4 verification at current HEAD passed 1,132 API tests against a
   disposable PostgreSQL database, plus 22 compiler and 17 converter tests.
   Baseline web tests passed 370 tests. The local browser nevertheless found
   incompatible persisted tutor state: this is a real demo-readiness issue,
   not a failed unit test. See the separate readiness report for final results.
3. A full redesign before Monday would be a poor research decision. The useful
   post-presentation design agenda is to run observed student/professor tasks,
   compare their independent performance, and simplify only the friction that
   the observations reveal.

## Suggested retrospective slide

**Title:** From AI tutor prototype to testable learning loop

Show five milestones: source-grounded canvas; professor feedback and embedded
practice; university identity/privacy boundary; live-content quality audit;
practice contract plus delayed-transfer measurement. Speak to the recurring
pattern: every major iteration tightened an authority or evidence boundary.
End with: "The prototype now makes a serious study possible. It has not yet
answered the study question."

## Local evidence used

- `.journal/2026-06-17-professor-demo-feedback.md`
- `local-course-materials/martius-ml/feedback/Feedback on Lecture 1.pdf`
- `local-course-materials/martius-ml/feedback/ideas_after_feedback2024.txt`
- `.learnings/softwarequality-canvas-pipeline-2026-07-26.md`
- `.learnings/softwarequalitaet-course-ingestion-2026-07-26.md`
- `design-qa.md`
- `docs/evaluation-contract.md`
- Git history from `36b190a` through `8e656e2`; commit dates checked September 4
