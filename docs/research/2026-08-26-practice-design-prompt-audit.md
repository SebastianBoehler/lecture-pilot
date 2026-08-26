# Practice-design prompt and contract audit

Research and code audit, 2026-08-26. Scope: the model proposal prompt, typed
contract, source validation, professor approval, canvas binding, learning-map
generation, and learner coaching path for one lecture.

## Verdict

**Needs critical follow-up before LecturePilot describes the generated plans as
pedagogically verified.** The architecture has unusually strong authority and
integrity controls: it uses structured output, exact source revisions, professor
approval, immutable design digests, generation preflight, and exact checkpoint
binding. The prompt also names the right instructional components: observable
capabilities, an immediate task, an unaided parallel task, delayed changed-form
transfer, criteria, misconceptions, and fading hints.

Those controls guarantee that an approved structure survives generation. They
do **not** guarantee that the model selected the right objective, that a task is
entailed by the cited material, that variants measure the same construct, or
that criteria and hints are instructionally sound. Several important approved
fields are also not consumed by the learner runtime. Prompt wording alone cannot
close these gaps; the design needs stronger evidence anchors, semantic review,
runtime wiring, professor-visible evidence, and provider benchmarks.

This verdict is the pre-hardening baseline. See **Resolution in this branch**
for the resulting controls and remaining evidence boundary.

The [MIT AI and Education report](https://aiandeducation.mit.edu/report/) is a
committee policy synthesis, not an efficacy trial or systematic evidence
review. Its useful direction is augmentation over automation, preservation of
productive struggle, backward design, human authority, and assessment of what
learners can do themselves. It should guide system objectives, not be cited as
proof that this implementation improves learning.

## What is enforced today

| Design element    | Prompt request                      | Mechanical enforcement                                                         | Learner-path use                                                                                            | Audit result                                                  |
| ----------------- | ----------------------------------- | ------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| Lecture objective | Implicitly requested by the schema  | Nonblank text only                                                             | Copied exactly to the learning map                                                                          | Alignment and realism are unchecked                           |
| Target outcome    | “Observable independent capability” | Rejects only outcomes beginning with `know` or `understand`                    | Used as review metadata                                                                                     | Many vague/non-assessable verbs still pass                    |
| Baseline task     | Source-grounded task                | Nonblank and textually unequal to the other two tasks                          | Exact approved text becomes one canonical checkpoint                                                        | Strong integrity; semantic grounding and difficulty unchecked |
| Independent exit  | Distinct parallel unaided task      | Nonblank and textually unequal                                                 | Stored in the learning map, but not included in active-gate context or issued by the coaching state machine | **Approved assessment is not operationalized**                |
| Delayed transfer  | Changed surface, same reasoning     | Nonblank, textually unequal, delay 1–365 days                                  | Exact prompt and delay are scheduled after a pass                                                           | Construct equivalence and delay rationale unchecked           |
| Evidence criteria | Precise criteria                    | At least one, stable unique IDs                                                | Exact criteria become the pass rubric                                                                       | No test of completeness, observability, or task alignment     |
| Misconceptions    | Diagnostic misconceptions           | Optional list with IDs and cues                                                | No learner-runtime consumer found                                                                           | **Professor reviews dead contract data**                      |
| Hint ladder       | Progressive approved hints          | Optional, unique enum levels in increasing order                               | No learner-runtime consumer found                                                                           | **Professor reviews dead contract data**                      |
| Source references | Exact authoritative paths           | Every path must occur in the confirmed manifest                                | Used for approximate section placement                                                                      | Path existence is checked; evidential entailment is not       |
| Authority         | Professor review and approval       | Source/design revisions and approval are frozen through generation/publication | Published map must remain bound to the approved revision                                                    | Strong                                                        |

Primary code evidence:

- The proposal prompt is a compact set of prose requirements:
  `apps/api/src/lecturepilot/course_practice_design_prompt.py:20-30`.
- Structural constraints are in
  `apps/api/src/lecturepilot/course_practice_design_models.py:45-98` and
  `apps/api/src/lecturepilot/course_practice_design_models.py:184-209`.
- Source validation checks only membership in the allowed path set:
  `apps/api/src/lecturepilot/course_practice_design_validation.py:49-59`.
- The source packet is capped at 80 sections/80,000 characters and 1,600
  characters for most blocks:
  `apps/api/src/lecturepilot/course_canvas_prompt.py:12-14` and
  `apps/api/src/lecturepilot/course_canvas_prompt.py:110-147`.
- Target-to-section assignment falls back to the first section when no source
  reference matches:
  `apps/api/src/lecturepilot/course_canvas_practice_contract.py:42-60`.
- The exact baseline, criteria, exit, transfer, and delay survive into the map:
  `apps/api/src/lecturepilot/learning_map.py:211-237`.
- Active tutor context includes baseline, criteria, transfer, and delay, but not
  the independent-exit task, hint ladder, or misconceptions:
  `apps/api/src/lecturepilot/model_client.py:270-287`.
- Standard attempts preceded by `prompt` assistance are currently classified as
  independent: `apps/api/src/lecturepilot/coaching_episode.py:110-115`.
- Revision-bound professor approval and generation preflight are enforced in
  `apps/api/src/lecturepilot/course_practice_design_store.py:92-160` and
  `apps/api/src/lecturepilot/course_practice_design_binding.py:77-152`.

## Prioritized findings

### P0 — Carry every approved teaching control into the learner runtime

`hint_ladder` and `misconceptions` disappear before the learning map. The
`independent_exit_task` reaches the map but is not a server-issued check. The
generic tutor may invent help despite the professor having approved exact
hints, and a supported pass can lead directly to delayed review without the
promised immediate unaided exit.

The analytics boundary also treats a check preceded by `prompt` assistance as
independent. That can be a defensible label for a content-free process prompt,
but it is not the strict `none`-assistance evidence the approved exit promises.

Required change:

1. Put misconception cues and approved hint steps in the revision-bound gate.
2. Let the server select the next allowed hint; do not ask the model to invent a
   pedagogical ladder at runtime.
3. After any supported success, issue the approved independent-exit task with
   assistance `none`; only an unaided pass should schedule delayed transfer.
4. Persist which approved hint was exposed and bind assessment to that exact
   attempt.

Why: in Bastani et al.'s nearly 1,000-student high-school math field experiment,
generic GPT improved assisted practice but harmed later unaided performance;
teacher-designed safeguards removed the harm but did not yield a positive
unaided gain over control. This supports guarded help and independent checks,
not a claim that any hint ladder improves learning
([Bastani et al., 2025](https://doi.org/10.1073/pnas.2422633122)).

### P0 — Replace path-level citation with field-level evidence

A valid `source_ref` proves only that a routed file exists. Because evidence is
truncated and balanced across sections, the allowed-path list can include a file
whose relevant content is absent from the model packet. A task can therefore
cite a real but unrelated file and pass validation. Downstream placement may
also fall back to an unrelated first section.

Required change:

1. Route a bounded source slice to each proposed target before target writing.
2. Require stable evidence anchors for the outcome, every task, every criterion,
   and every content-bearing hint—not one path list for the whole target.
3. Validate that anchors exist in the exact source revision and place the
   checkpoint only in a section carrying one of those anchors; remove fallback
   placement.
4. Show the supporting excerpt beside each professor review field.
5. Run a separate source-entailment review and fail closed on unsupported or
   incomplete claims; treat model review as a benchmarked safeguard, not a
   deterministic guarantee.

Why: a randomized study of 274 online adult learners found that validated
LLM-generated mathematics hints could support immediate learning, but raw
generated help failed human quality checks for 32% of problems. The authors
quality-screened all exposed hints; source access alone was not sufficient
([Pardos & Bhandari, 2024](https://doi.org/10.1371/journal.pone.0304013)).

### P0 — Validate alignment, not merely shape and string difference

The current contract rejects exact duplicate task strings, not construct drift,
answer leakage, irrelevant difficulty changes, or a transfer task requiring
facts outside the lecture. It also accepts outcomes such as “appreciate,” “be
familiar with,” or “learn about.” Evidence criteria may be vague or omit the
reasoning the task is supposed to reveal.

Required change:

- Define every outcome as **conditions + observable action + acceptable
  evidence/standard**, at the lecture's stated learner level.
- Require an explicit `target_invariant`: the knowledge or reasoning operation
  held constant across task variants.
- Require each variant to state what changed and why no new unprovided knowledge
  is needed.
- Require atomic criteria that can be judged from learner work, cover the
  invariant, and do not pass on keywords alone.
- Add a source-and-alignment critic with bounded repair, then expose unresolved
  concerns to the professor. Add deterministic checks for anchors, answer
  leakage, empty criteria, duplicate variants, and stable IDs; do not call the
  remaining semantic checks deterministic.

This is standard backward-design logic: identify desired results, determine
acceptable evidence, then plan learning activities. MIT's official guidance
also says outcomes should be specific, measurable, realistic for learners and
time, student-centered, and assessed with tasks matching the stated action
([MIT Teaching + Learning Lab](https://tll.mit.edu/teaching-resources/course-design/backward-design/)).

### P1 — Clarify the three assessment stages

“Baseline task” is ambiguous. In the product it becomes a checkpoint after the
relevant generated instruction, not necessarily a pre-instruction diagnostic.
The prompt should define:

- **Diagnostic attempt:** before substantive help, used to choose support; not a
  mastery claim.
- **Independent exit:** a parallel task after help, issued without help and not
  visible during instruction.
- **Delayed transfer:** a later changed-form task preserving the invariant.

Repeated retrieval with feedback beat restudy on one-week retention and
inferential transfer across four small undergraduate experiments, but transfer
was conditional and should not be generalized to arbitrary far-transfer tasks
([Butler, 2010](https://doi.org/10.1037/a0019902)). Therefore “changed surface”
must mean a controlled change around the same capability, not simply “harder” or
“a different domain.”

### P1 — Make scaffolding adaptive and defined

The enum order `prompt → cue → faded_example → worked_step` is enforced, but the
levels are not defined for the planner and can leak the answer. Define them:

- `prompt`: asks the learner to inspect or plan; no domain answer content.
- `cue`: names the relevant principle or representation, not the next answer.
- `faded_example`: an analogous partially completed example with at least one
  learner-owned step.
- `worked_step`: one justified step only, followed by a new learner-owned step.

Two experiments with psychology undergraduates and high-school students found
that faded worked examples combined with self-explanation prompts improved near
and far transfer in probability learning; this is narrow evidence, not a
universal sequence for all disciplines
([Atkinson, Renkl, & Merrill, 2003](https://doi.org/10.1037/0022-0663.95.4.774)).
The classic deliberate-practice account likewise describes well-defined tasks,
focused improvement, feedback, and repeated correction; one generated task per
stage is only _aligned with_ this idea, not itself deliberate practice
([Ericsson, Krampe, & Tesch-Römer, 1993](https://doi.org/10.1037/0033-295X.100.3.363)).

### P1 — Add learner context and light metacognition

The planner sees lecture sources but no course level, prerequisites, expected
time, assessment conditions, allowed aids, or learner population. It cannot
judge whether an objective is realistic or a task is appropriately difficult.
It also does not design confidence calibration, strategy selection, or
self-explanation.

Required change:

- Pass professor-controlled course level, prerequisites, time budget, allowed
  tools, and assessment conditions into the planner.
- Add a brief explain-back criterion when reasoning is the target.
- Collect confidence before feedback on diagnostic, exit, and transfer tasks;
  use the gap between confidence and performance for later support, never as a
  grade.
- Ask for a next strategy after feedback only when it changes the next attempt.

Prompted self-explanation improved conceptual integration in a small study of
24 eighth-graders, so it is a promising targeted move, not a reason to require
reflection after every item
([Chi et al., 1994](https://doi.org/10.1207/s15516709cog1803_3)). A randomized
one-session study of 87 college students found metacognitive chatbot feedback
improved transfer and confidence–accuracy sensitivity versus neutral feedback;
its small, narrow design does not establish a universal effect
([Yin et al., 2025](https://doi.org/10.1038/s41539-025-00311-8)). Zimmerman's
source model organizes self-regulated learning as forethought, performance, and
self-reflection
([Zimmerman, 2002](https://doi.org/10.1207/S15430421TIP4102_2)).

### P2 — Remove arbitrary granularity and scheduling cues

The prose asks for 3–6 targets while the schema permits 1–8. Neither range is an
evidence-based quality rule. Keep only the minimum set of distinct capabilities
needed to represent the source and fail when evidence is too thin. Likewise,
`review_after_days` is currently a free model choice from 1–365. A scheduler
should use course/exam constraints and learner performance; the planner may
propose a rationale, but the number should not be presented as scientifically
optimal.

## Minimum revised planner instruction

The next prompt should explicitly say, in substance:

> Optimize for the learner's delayed, unaided ability to perform the approved
> capability; assisted completion is not evidence of learning. Work backward
> from source-supported, student-centered outcomes to acceptable evidence and
> then practice. Use only supplied evidence anchors. If the source or learner
> context cannot support a realistic objective, task, criterion, misconception,
> or hint, omit it or return an explicit insufficiency—never invent it. For each
> target define the invariant reasoning, a diagnostic attempt, a parallel
> unaided exit, and a delayed changed-form transfer task. State what changes
> across variants and ensure no new unprovided knowledge is required. Make
> criteria atomic and observable. Hints must follow the defined ladder, reveal
> only the minimum next information, and return work to the learner. Do not
> equate engagement, speed, confidence, or assisted correctness with mastery.

That wording is necessary but not sufficient. The response schema, validators,
runtime, professor review, and benchmark must implement the same contract.

## Verification before claiming pedagogical readiness

1. Build a frozen, multi-discipline benchmark of real lecture packets with
   professor-authored gold outcomes, task invariants, acceptable variants,
   criteria, and evidence anchors.
2. Blind-rate model proposals for source entailment, outcome–assessment
   alignment, task equivalence, answer leakage, difficulty, misconception
   usefulness, hint correctness, and transfer validity. Report disagreement;
   do not reduce review to one aggregate score.
3. Adversarially test thin, contradictory, multilingual, mathematical, code,
   table, and very large source packets. Confirm the system refuses unsupported
   designs rather than producing plausible ones.
4. Run the real provider and exact production response schema; deterministic
   fixture tests establish plumbing, not proposal quality.
5. Only a prospective study with unaided exit and delayed changed-form outcomes
   can establish that LecturePilot improves learning. Assisted correctness and
   professor approval establish neither efficacy nor transfer.

## Bottom line

The current design is a strong **professor-controlled integrity contract** and a
promising pedagogical scaffold. It is not yet a verified pedagogical planner.
The critical sequence is: field-level evidence → semantic alignment review →
professor-visible excerpts → exact runtime consumption of exit/misconception/
hints → provider benchmark → delayed unaided learner evaluation.

## Resolution in this branch

Every generated field now has a validated, visible source excerpt. A separate
critic checks entailment, alignment, invariant preservation, leakage, difficulty,
rubric quality, and coverage. The revision-bound map carries approved hints and
misconceptions; the server administers diagnostic, support, unaided exit, and
delayed transfer. Edits require re-review. The benchmark reports dimensional
scores, disagreement, and failures.

These controls do not establish learning efficacy. That still requires a
prospective evaluation using unaided exit and delayed transfer outcomes.
