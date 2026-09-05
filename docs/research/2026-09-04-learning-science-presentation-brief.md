# LecturePilot: learning-science presentation brief

Prepared 2026-09-04 for the presentation described by the student as a nine-ECTS
University of Tübingen research project on Monday, 2026-09-07. Date and credit
requirements have not been independently checked against a university record.
This is a design rationale, **not** an efficacy claim: the repository includes
an evaluation contract, but does not document a completed learner study,
institutional study approval, or a causal learning result.

## One-minute narrative

LecturePilot is not a generic course chatbot. It constrains an AI tutor to
professor-authorized, already-unlocked material and uses the canvas as the
student's working surface. The central design choice is to protect the learning
act: students make a diagnostic attempt, receive source-grounded support when
needed, and attempt an independent exit task; a later changed task asks whether
the reasoning transfers without help. Novices may need instruction or a worked
step before a meaningful full solution attempt. This is a CPU-only control
plane around provider inference, not a locally hosted foundation model.

The scientific contribution is therefore a **testable learning interaction and
measurement contract**, not the claim that AI conversation itself causes
learning. It separates (1) supported recovery, (2) independent exit
performance, and (3) delayed, changed-form transfer.

## Evidence-to-product map

| Learning principle            | What the evidence supports                                                                                                                                                                                                                                                                                            | LecturePilot implementation / intended behavior                                                                                                               | Claim boundary for the presentation                                                                                                                                  |
| ----------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Retrieval practice            | Taking tests/practising retrieval generally improves classroom learning relative to comparison conditions; effects depend on feedback, test format, and setting. [Yang et al., 2021](https://doi.org/10.1037/bul0000309)                                                                                              | Source-backed quizzes, checkpoints, and an attempt-before-feedback tutor posture.                                                                             | **Established principle; product application.** Do not say the current product has demonstrated retention gains.                                                     |
| Deliberate practice           | Purposeful, feedback-informed practice is important in expertise research, but it explains only part of performance variation and is not a universal recipe. [Ericsson et al., 1993](https://doi.org/10.1037/0033-295X.100.3.363); [Macnamara et al., 2014](https://doi.org/10.1177/0956797614535810)                 | Professor-approved observable targets, criteria, misconceptions, baseline task, and progressive hint ladder.                                                  | **Design inspiration, not a causal product claim.** Avoid claiming “deliberate practice guarantees expertise.”                                                       |
| Worked examples and fading    | Worked examples can be more efficient than unguided problem solving for novices; the advantage depends on design and prior knowledge, and can reverse for more expert learners. [Sweller et al., 2019](https://doi.org/10.1007/s10648-019-09465-5); [Ward & Sweller, 1990](https://doi.org/10.1207/s1532690xci0701_1) | The approved ladder progresses from prompt/cue to faded example/worked step; it must be released after evidence, then faded for later independent checks.     | **Established instructional pattern; adaptation rule is a product hypothesis** until learner outcomes validate it.                                                   |
| Feedback and adaptive support | Feedback has a positive average effect but varies substantially; information that helps a learner act on the task/process is more defensible than praise or a correctness label alone. [Wisniewski et al., 2020](https://doi.org/10.3389/fpsyg.2019.03087)                                                            | Tutor feedback is meant to respond to an observed attempt, identify the next action, stay within the approved assistance level, and retain source provenance. | **Evidence-informed.** A generative tutor's feedback quality and adaptation are not established by the general feedback literature.                                  |
| Delayed unaided transfer      | Retrieval can transfer, but transfer effects are smaller and conditional; overlap between practice and target, initial retrieval success, and elaboration matter. [Pan & Rickard, 2018](https://doi.org/10.1037/bul0000151)                                                                                           | A delayed task changes surface features while preserving the target reasoning; assistance level and planned/observed delay are revision-bound outcomes.       | **Strong measurement choice, not a proven product effect.** A changed task is more credible than repeating an identical quiz, but is not automatically far transfer. |
| Self-regulated learning       | Structured plan–monitor–reflect interventions show positive average outcomes in higher education, with meaningful variation by design. [Theobald, 2021](https://doi.org/10.1016/j.cedpsych.2021.101976)                                                                                                               | Learner-specific notes, progress, targeted checks, and a tutor that asks for evidence rather than silently completing the task.                               | **Evidence-informed direction.** Reflection prompts alone are not evidence of self-regulation or learning.                                                           |

Spacing complements the table: distributed practice supports retention, but
the useful spacing interval depends on the intended retention interval and
task. [Cepeda et al. (2006)](https://doi.org/10.1037/0033-2909.132.3.354)
supports revisiting material across time; it does **not** establish that a
model-selected `review_after_days` is optimal. A delayed assessment measures
retention/transfer; offering it alone does not prove a spacing benefit.

“Deliberate-practice-inspired” is the safer product label: explicit targets,
diagnostic attempts, feedback and retries borrow from that tradition. A quiz
button or repeated chat is not sufficient evidence of deliberate practice.
The 1993 expertise study is historical framing, not an experiment on AI tutors;
the later meta-analysis is correlational evidence with domain-dependent results,
not an estimate of LecturePilot's treatment effect.

## What is implemented versus what remains to validate

Source inspection below is against commit `8e656e2` after reconciling the
checkout on 2026-09-04. This is not a claim that every path has passed live
provider or browser testing in this research pass.

- The teacher owns source material, schedule, learning goals, permissible
  scaffolds, and publication approval; the model cannot approve its own plan.
  The [practice models](../../apps/api/src/lecturepilot/course_practice_design_models.py)
  contain observable outcomes, exact source anchors, criteria, three distinct
  tasks, an ordered hint ladder, and a proposed review interval.
  [Generation readiness](../../apps/api/src/lecturepilot/course_practice_design_readiness.py)
  requires approval for the current source and practice-design revisions.
  Distinct task strings and valid anchors are structural checks, not proof of
  pedagogical equivalence, correctness, or useful difficulty.
- [Coaching transitions](../../apps/api/src/lecturepilot/coaching_transitions.py)
  distinguish diagnostics, supported retries, independent exits and delayed
  checks. The backend selects the next approved hint and returns to an unaided
  check after supported success. The
  [scaffold policy](../../apps/api/src/lecturepilot/scaffold_policy.py) also
  supports novice worked steps. This is not a universal “withhold all help” rule.
  A post-support retry of an already-seen exit task must not be reported as
  first-attempt independence on a novel task.
  These existing state-machine mechanics do not establish comprehensive learner
  policy enforcement: [AGENTS.md](../../AGENTS.md#agent-harness-rules) explicitly
  limits the practice-authoring slice to recording future independent-exit and
  scaffold intent, without adding learner-runtime SRL or AI-policy enforcement.
- The runtime is designed to distinguish attendance context, checkpoints,
  quizzes, learner-owned notes, and quality gates. Attendance changes tutor
  stance rather than creating a separate learner schema. See [README](../../README.md).
- The evaluation contract defines delayed independent performance on a changed
  task as the future primary measure; assisted recovery and first independent
  attempt are secondary. It excludes raw learner text from professor aggregates
  and marks the study as future work. See [evaluation contract](../evaluation-contract.md).
- The web/API host is CPU-only; model and image inference stay behind a configured
  provider boundary. Shared course sources and learner overlays avoid a model
  or full source copy per learner. See [hosting footprint](../../README.md#small-hosting-footprint)
  and [workspace contract](../../AGENTS.md#agent-storage-image). Resource limits
  are ceilings, not measured host requirements or concurrent-student capacity.
  External inference, storage, conversion work and operations still cost money.

## Product hypotheses to test, not assert

1. An attempt-first, source-grounded, assistance-fading tutor improves delayed
   independent changed-form performance over an otherwise comparable source
   canvas or ordinary general-purpose AI.
2. Typed assistance level and guidance mode predict a meaningful distinction
   between “recovered with help,” “independent now,” and “retained/transferred
   later.”
3. Attendance-aware tutor stance improves continuity or support without
   unfairly changing the learning standard. There is **no** basis to claim that
   attendance tracking or gates themselves cause learning.
4. A small, provider-routed architecture can give a university a lower local
   compute/operations footprint; this is an engineering property, not evidence
   of cheaper total service or educational efficacy.

For UI decisions, keep the task, relevant source and learner's work close
together; show one next action and feedback that names a usable next step.
Make help versus independent-check states legible, and permit source inspection
without losing the current task. These are evidence-informed design proposals,
not a claim that this layout has been experimentally optimized. Measure task
completion errors and learner outcomes; screenshots and unit tests cannot
validate pedagogy.

## Tübingen and Georg Martius: accurate context

Professor Dr. Georg Martius heads the University of Tübingen
Distributed Intelligence / Autonomous Learning group. The group's stated focus
is embodied agents deciding what and how to learn, evaluated in real-world
robotic systems; it works on reinforcement, representation, and internal-model
learning. It is **not accurately described as an autonomous-driving lab**.

This makes a careful conceptual bridge, not an evidential shortcut: both lines
of work care about learning under constraints, evaluation, and adaptation. But
robot autonomy/reinforcement learning does **not** validate a human-learning
intervention. LecturePilot's relevant human-learning claims must be tested with
students and educational outcomes.

Official context: [University group page](https://uni-tuebingen.de/en/264672).
The project relationship is provided by the student; this page does not certify
supervision, project credits, endorsement or specific feedback attribution.

### Direct local learning-research bridge

**Feedback: Wagner et al. (2024), not “Wager.”** Three online experiments with
university students studied electric-circuit troubleshooting. Combining strategy
instruction with corrective feedback gave no additive benefit in Experiment 1
and reduced the instruction benefit on its far-transfer measure. Combining
instruction with elaborated feedback produced additive effects in Experiment 2;
Experiment 3 found these across both tested instruction/practice sequences.
[Publisher article](https://www.sciencedirect.com/science/article/pii/S0959475223001135),
[TüCeDE report](https://uni-tuebingen.de/forschung/zentren-und-institute/tuebingen-center-for-digital-education/newsfullview-tuecede/article/the-more-the-better/).

Our inference: design feedback to address a specific reasoning gap and give a
usable next step. Neither “more text is better” nor “shorter is always better”
follows from this study; it does not test generative tutoring or our UI.

**Teaching quality: ETQ-AI.** Tübingen's project aims to give teachers formative
feedback using classroom audio/transcripts, including instructional organization,
cognitive stimulation, and encouragement/warmth. It is teacher-facing, not a
validated LecturePilot tutor or a source of learner-effect estimates.
[Official project](https://uni-tuebingen.de/en/281061).
Our inference: professor review should inspect instructional decisions rather
than approve generated text only. Audio collection is not proposed for LecturePilot.

These are relevant local research connections, not evidence that those teams
collaborated on or endorsed this project. Martius's robotics research remains a
conceptual connection to constrained adaptation, not human-learning validation.

## Suggested six-slide spine

1. **Problem:** receiving a fluent answer is not evidence of independent
   competence; universities need learning evidence, source authority, and
   manageable operational burden.
2. **Thesis:** turn the tutor from answer generator into an evidence-gated
   learning loop: _attempt → calibrated help → independent exit → delayed
   changed-form transfer_.
3. **Learning science:** retrieval, novice examples with fading, actionable
   feedback, and deliberate practice constraints. Use the evidence/product
   distinction from the table.
4. **System:** professor-approved sources and practice design → constrained
   backend tools → learner canvas and revision-bound outcomes. Emphasize that
   backend policy, rather than the prompt, enforces the boundary.
5. **Research contribution:** outcomes separate support from independence and
   transfer; a future study should compare variants on delayed unaided
   changed-form tasks, report missing follow-up and preserve revision boundaries.
6. **Tübingen fit and next test:** Martius's autonomous-learning context
   motivates rigorous adaptation and evaluation, while the next credible step
   is a consented learner study—not a claim of effectiveness today.

## References and access record

Checked on 2026-09-04 using publisher records, the authors' repository for Pan
and Rickard, and official university pages. Some DOI direct opens were blocked;
indexed publisher abstracts supported the limited claims above. This was not a
full-text systematic review. Ericsson (1993) and Ward and Sweller (1990) remain
background references; their full texts were not independently inspected here.

1. Yang, C., Luo, L., Vadillo, M. A., Yu, R., & Shanks, D. R. (2021).
   _Testing (quizzing) boosts classroom learning: A systematic and
   meta-analytic review._ Psychological Bulletin, 147(4), 399–435.
   https://doi.org/10.1037/bul0000309
2. Ericsson, K. A., Krampe, R. T., & Tesch-Römer, C. (1993). _The role of
   deliberate practice in the acquisition of expert performance._ Psychological
   Review, 100(3), 363–406. https://doi.org/10.1037/0033-295X.100.3.363
3. Macnamara, B. N., Hambrick, D. Z., & Oswald, F. L. (2014). _Deliberate
   practice and performance in music, games, sports, education, and
   professions: A meta-analysis._ Psychological Science, 25(8), 1608–1618.
   https://doi.org/10.1177/0956797614535810
4. Sweller, J., van Merriënboer, J. J. G., & Paas, F. (2019). _Cognitive
   architecture and instructional design: 20 years later._ Educational
   Psychology Review, 31, 261–292. https://doi.org/10.1007/s10648-019-09465-5
5. Ward, M., & Sweller, J. (1990). _Structuring effective worked examples._
   Cognition and Instruction, 7(1), 1–39.
   https://doi.org/10.1207/s1532690xci0701_1
6. Wisniewski, B., Zierer, K., & Hattie, J. (2020). _The power of feedback
   revisited: A meta-analysis of educational feedback research._ Frontiers in
   Psychology, 10, 3087. https://doi.org/10.3389/fpsyg.2019.03087
7. Pan, S. C., & Rickard, T. C. (2018). _Transfer of test-enhanced learning:
   Meta-analytic review and synthesis._ Psychological Bulletin, 144(7),
   710–756. https://doi.org/10.1037/bul0000151
8. Theobald, M. (2021). _Self-regulated learning training programs enhance
   university students' academic performance, self-regulated learning
   strategies, and motivation: A meta-analysis._ Contemporary Educational
   Psychology, 66, 101976. https://doi.org/10.1016/j.cedpsych.2021.101976
9. Wagner, S., Sibley, L., Weiler, D. C., Burde, J.-P., Scheiter, K., &
   Lachner, A. (2024). _The more, the better? Learning with feedback and
   instruction._ Learning and Instruction, 89, 101844.
   https://doi.org/10.1016/j.learninstruc.2023.101844. See also the
   [University of Tübingen report](https://uni-tuebingen.de/forschung/zentren-und-institute/tuebingen-center-for-digital-education/newsfullview-tuecede/article/the-more-the-better/).
10. Cepeda, N. J., Pashler, H., Vul, E., Wixted, J. T., & Rohrer, D. (2006).
    _Distributed practice in verbal recall tasks: A review and quantitative
    synthesis._ Psychological Bulletin, 132(3), 354–380.
    https://doi.org/10.1037/0033-2909.132.3.354

## Presenter guardrails

- Say “designed to test,” “evidence-informed,” and “intended primary outcome,”
  never “proven to improve learning.”
- Say “delayed changed-form transfer,” not “far transfer,” unless the study
  truly tests a distant domain/context.
- Do not attribute human learning-science conclusions to Martius's robotics
  research, or describe his group as autonomous driving.
- Attendance is context, not a validated measure of expertise; source grounding
  is provenance, not a guarantee of correctness; completed gates are not an
  independently validated mastery score.
- No provider/model change, API availability or price claim is recommended by
  this brief. Codex-assisted development is separate from deployed inference.
