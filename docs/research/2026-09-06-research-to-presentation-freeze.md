# A final research-informed iteration for LecturePilot

Prepared 6 September 2026 for tomorrow's presentation. Current implementation
inspected at `cb4f771`. Priority: a defensible scientific account and a few small
improvements. This report proposes the final app iteration; it does not claim
that those additional changes, a deployment or an efficacy study have occurred.

Implementation follow-through: [final verification and presentation record](2026-09-06-final-iteration-verification.md).

## Recommendation

Keep the current architecture and make the final pass about **the reasoning a
student performs, the validity of its assessment, and a reproducible demonstration**.
LecturePilot already has the important building blocks. A new media platform or
another autonomous agent would increase the amount to validate before tomorrow.

The strongest product thesis is:

> The professor defines the capability and evidence. LecturePilot prepares and
> adapts source-backed teaching, while distinguishing assisted success from a
> fresh independent attempt and a later demonstration.

That is a research-informed engineering contribution. Whether it improves
learning, for whom, and at what delivery cost remains an empirical question.

“Independent” in the current UI means independently **in this app**. Focused
attempts close its teaching and chat and record requested help. This does not
verify the absence of another device, external AI or outside assistance. A study
needs an explicit assessment-access protocol; a product label cannot supply it.

## What the literature changes in our thinking

### The learning operation should determine the display

There is no single best medium across tasks. In one experiment, animation helped
identify motion while static pictures helped identify spatial arrangements.
In another series, prediction and explanation improved mechanical understanding
without animation superiority. These outcomes support selective media choice,
not a universal static-first or animation-first rule.
[Ploetzner et al. 2021](https://doi.org/10.1007/s11251-021-09541-w),
[Hegarty et al. 2003](https://tecfa.unige.ch/tecfa/teaching/methodo/hegarty03.pdf).

| Capability being taught            | Suitable current LecturePilot surface | What makes the interaction meaningful                              |
| ---------------------------------- | ------------------------------------- | ------------------------------------------------------------------ |
| Compare explanations or conditions | Comparison component, grid or table   | Alternatives stay visible with shared quantities and scales.       |
| Trace an algorithm or causal chain | Process explorer or flow              | The learner anticipates and explains a state change.               |
| Reason about a parameter           | Interactive chart plus its data table | Change one defined parameter and explain the verified consequence. |
| Understand a relationship          | Diagram, formula and adjacent prose   | Labels and explanation make the relevant relation explicit.        |
| Learn detailed motion              | Appropriate existing source video     | Pause and inspect the motion that the later task actually tests.   |

This mapping is a design inference. The app already has these component families,
nearby explanations, numeric data tables and source references. Its authoring
catalogue already asks for purposeful media. The proposed refinement is selective
prediction/principle explanation and review of whether the example supports it.

### Interaction should elicit reasoning without making every action a test

Computer-based probability experiments support combining faded examples with
principle-focused self-explanation for immediate transfer. This is a reason to
ask why a step works and gradually return work to the learner. It is not a reason
to withhold teaching from a novice or force a question after every sentence.
[Atkinson, Renkl & Merrill 2003](https://doi.org/10.1037/0022-0663.95.4.774).

A useful teaching sequence is **inspect the givens → predict → change or reveal
one thing → explain the result**. Use it where the learner can form a meaningful
prediction. Keep optional exploration separate from assessment: moving a control,
reading its explanation or guessing correctly must not pass an independent gate.

A useful check on our enthusiasm is research already cited inside the app:
Lachner and colleagues' 2025 participant-level synthesis of three secondary-physics
experiments, with 1,074 learners, found an immediate benefit of explaining to a
fictitious peer but no overall eight-week benefit. Learners recorded tablet voice
messages after instruction; this was not a conversational AI tutor. Reported
subgroup differences do not justify assigning students a permanent learning type.
The implication is to test durable outcomes even for promising explanation prompts.
[Original study and methods](https://link.springer.com/article/10.1007/s10648-025-10060-0).

### Neuroscience explains plausible mechanisms, not app efficacy

Retrieval experiments connect later recall with hippocampal and semantic-system
activity; intensive spacing research connects benefits with re-encoding. Neither
establishes a neural measure of LecturePilot mastery or an optimal review interval.
[Wing et al. 2013](https://doi.org/10.1016/j.neuropsychologia.2013.04.004),
[Zou et al. 2025](https://doi.org/10.1016/j.celrep.2025.115232).

Curiosity also needs a target: a 2024 experiment found poorer memory for unrelated
facts around engaging trivia. A concept-relevant puzzle is a better candidate
than unrelated rewards or entertainment.
[Keller et al. 2024](https://doi.org/10.1038/s41539-024-00234-w).

The defensible neural story is that encoding, retrieval and consolidation are
processes over time. Actual independent behavior is the appropriate product
evidence. EEG activation, pupil size, enjoyment and confidence are different
measurements. None is a substitute for conceptual application.

### VR and games are conditional possibilities

One desktop-versus-headset experiment found greater presence but lower knowledge
gains in VR, without significant transfer differences. A later field-trip study
favored VR, but its delayed test followed additional instruction and its comparison
also changed individual versus projected presentation. The evidence does not
select a universal device winner.
[Makransky et al. 2019](https://doi.org/10.1016/j.learninstruc.2017.12.007),
[Makransky & Mayer 2022](https://doi.org/10.1007/s10648-022-09675-4).

Meta-analyses find benefits for some games and gamification, with heterogeneous
interventions and important comparator effects. This supports testing a defined
challenge, not assigning a pooled effect to points or badges.
[Sitzmann 2011](https://doi.org/10.1111/j.1744-6570.2011.01190.x),
[Sailer & Homner 2020](https://doi.org/10.1007/s10648-019-09498-w).

For this app, a small task such as explaining a model trade-off can use game-like
challenge and feedback inside an existing chart. A VR study would need a concept
whose spatial or embodied affordance is plausibly useful, plus a strong desktop
comparator. That is a separate experiment after the presentation.

### AI learning evidence is mixed, and outcome definitions matter

Bastani's guarded tutor mitigated the unaided-performance harm of ordinary AI
assistance without establishing an unaided gain. Contractor and Reyes' July 2026
working paper reports a positive one-week knowledge-test effect from ordinary AI
access, with integrity and measurement caveats. These results caution against a
simple claim that unrestricted AI always harms learning or that guardrails guarantee it.
[Bastani et al.](https://hamsabastani.github.io/education_llm.pdf),
[Contractor & Reyes](https://docs.iza.org/dp18792.pdf).

Purpose-built lessons, assistance to human tutors and expert-supervised AI are
distinct interventions. The LearnLM/Eedi report's next-topic result is same-day,
human-supervised and uncertain relative to human-only tutoring. Expert preference,
same-session success and delayed independent performance must stay separate.
[Kestin et al.](https://pubmed.ncbi.nlm.nih.gov/40537565/),
[Tutor CoPilot](https://arxiv.org/html/2410.03017v2),
[LearnLM/Eedi](https://arxiv.org/html/2512.23633v1).

## The final implementation pass I recommend

### 1. Refine existing teaching and review guidance

Scope: `course_teaching_instructions.py`, `canvas_component_catalog.py` and the
review guidance that consumes them. Add a short instruction to choose the display
from the observable operation and, where useful, ask for a prediction or principle
explanation. Preserve the existing component schema and professor-approved tasks.
Use the existing component prompt and frame explanation fields; introduce no
universal visual, question or click quota.

Also make the learner-facing `LearningScienceArticle.tsx` advice less absolute:
when prerequisites are missing, start with a worked example, then ask the learner
to complete or explain the next step. Its current “only look at the full solution
after” wording overlooks that teaching need. This is a small copy refinement,
consistent with the tutor prompt's existing prerequisite exception.

Success check: review one source-backed concept in its actual canvas. The learner
can identify the givens, make the intended comparison, and explain its consequence.
Units, labels, alternatives and supporting source agree. The teaching example
does not reuse a hidden assessment. Reapprove changed teaching through the current
workflow; do not regenerate the entire presentation course.

Illustrative pattern, not newly approved course content: a threshold example can
show that, for fixed model scores, raising the threshold cannot increase predicted
positives; their count may stay unchanged. Precision need not rise and is undefined
if no predicted positives remain. Ask for the prediction, show exact cases/counts,
then request an explanation of the denominator. The later independent task uses
different approved data. This tests a reasoning relationship, not slider use.

### 2. Align the benchmark with the actual assessment flow

The current six-scenario gate benchmark omits the explicit checkpoint flag and
issued task ID. A read-only construction check confirmed both omissions for all
six cases. It uses shared model infrastructure but does not reproduce the new
checkpoint contract. Correct this verification gap before relying on its score.

Scope: the existing benchmark and small scenario/contract helpers, using existing
API regressions for persistence rather than adding another evaluation framework.
Bind the exact task, source, rubric, publication, stage and issuance identity.
Test valid alternate
reasoning, misleading keywords, wrong reasoning with a correct result, incomplete
answers, support exposure, fresh tasks and stale submissions. Expected evidence
must follow the approved rubric; answer length is not correctness.

Success check: separate false passes, false rejections and contract failures;
verify persisted support/independent transitions through the normal API path.
Human-review the small answer set. Keep provider-quality checks out of deterministic
CI and state exactly which model and cases ran. This is release validation, not
a measured population grading accuracy or learning effect.
[MRBench](https://aclanthology.org/2025.naacl-long.57/),
[MathTutorBench](https://aclanthology.org/2025.emnlp-main.11/) motivate separate
pedagogical diagnostics rather than a single fluency or solving score.

### 3. Freeze a reproducible presentation path

Select one already published lecture and record its code revision, publication,
source/design revisions, reviewed language variant and configured provider/model.
Use the prepared content for the live demonstration. Rehearse one incorrect
attempt, approved support, a fresh independent task, reload and an in-app source.
Show the scheduled later review as a future observation; do not fast-forward a
clock and call the resulting transition evidence of retention.

Before calling the presentation ready, verify the actual browser flow at the
presentation viewport and one narrow viewport, keyboard controls, light/dark
mode, source loading, and visible provider-error behavior. Preserve the checks
already passed; rerun the affected tests/build after the final changes. Record
any remaining failure explicitly. Stop authoring jobs before the live demo so
they do not compete for inference capacity. No provider, dependency or storage
migration belongs in this final pass without an observed blocking defect.

## The next substantive improvements after the presentation

1. **Criterion-linked assistance.** Post-assessment guidance advances through
   unexposed approved hints; explicit help starts with the first approved hint.
   Neither selects by the specific missing evidence IDs. Bind reviewed hints to
   criteria/misconceptions, then select from observed gaps. This requires a proper
   contract change and semantic review.
2. **Better task validity.** Review whether variants demand the same capability
   and distinguish changed wording, near transfer and genuinely new application.
   New numbers alone do not establish transfer or equal difficulty.
   [Pan & Rickard 2017](https://doi.org/10.1037/xap0000124).
3. **Calibrated assessment.** Compare evidence decisions with independent expert
   labels, including correct concise answers, language variation and boundary
   cases. Keep disagreement and uncertainty visible in evaluation.
4. **A small causal learning experiment.** Compare the same approved visual with
   and without selective prediction/explanation under matched study opportunity.
   Predefine prior-knowledge measures, delayed fresh-task scoring, attrition and
   the analysis. Choose the follow-up interval for the research question, not
   from a claimed universal brain schedule. A broader whole-app comparison is a
   different experiment. Determine sample size from a justified precision/power
   target and obtain the required study approvals before recruiting.

## Presentation-ready scientific wording

“LecturePilot turns professor-approved learning goals into source-backed teaching
and checks. Its design draws on retrieval, guided examples, fading and multimedia
learning research. We can demonstrate the workflow and its software controls.
The next study asks whether students later solve a changed task independently.”

For a neuroscience question: “Memory changes through encoding, retrieval and
consolidation. Brain studies help motivate hypotheses, but we measure learning
through behavior. We do not infer mastery from brain signals.”

For an architecture question: “The model proposes content and evidence judgments;
the backend owns authority, task state and transitions. Professor approval controls
sources and publication. We evaluate instructional quality separately from schema
validity and from real learner outcomes.”

## Evidence and scope

Research block: approximately 12:53–13:23 UTC on 6 September (14:53–15:23 Berlin),
including primary-source reading, independent critical review, current-code checks
and synthesis. This was about 30 minutes of elapsed work, not a multi-day review.

- [Neuroscience ledger](2026-09-06-neuroscience-learning-evidence.md): ten original
  peer-reviewed papers plus a bounded preliminary EEG/AI-writing discussion.
- [Display/media ledger](2026-09-06-display-media-learning-evidence.md): eight
  original experiments and two meta-analyses, with full-text access limits stated.
- [AI and evaluation update](2026-09-06-ai-learning-and-evaluation-update.md):
  learner trials, supervised systems, tutor benchmarks, laptop replication and
  the current-code findings.

This was a bounded critical search, not a systematic review. It inspected primary
sources and sought counterexamples, outcome timing and comparator differences.
Some publisher access was blocked; those entries are explicitly qualified.
Query families covered retrieval/spacing neuroimaging; curiosity and incidental
learning; prediction, self-explanation and animation; desktop versus immersive VR;
simulation games/gamification; randomized AI learning and delayed tests; tutor
evaluation benchmarks; and laptop note-taking replication. Searches used PubMed,
arXiv, ACL Anthology, IZA and publisher/author copies. Original experiments were
prioritized, with two explicitly labeled media meta-analyses for broader context.
The final pass also checked the app's existing 2025 participant-level synthesis
of explaining to a peer and current version metadata for the AI preprints.
The ledgers record population, tested outcome, timing and limits; no exhaustive
screening count or publication-bias-adjusted synthesis is claimed.
No learner data, source corpus, runtime behavior or production deployment was
changed during research. The remaining implementation and freeze checks above
are proposed work, not completed verification.

Artifact verification: scoped Prettier checks, repository local-link validation
and whitespace checks passed. The benchmark-construction command reproduced the
six missing bindings without making provider calls. Application tests and a live
browser rehearsal were not rerun for these research-only documents.
