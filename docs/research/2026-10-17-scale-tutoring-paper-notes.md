# SCALE tutoring studies: full-text reading notes

Read 17 October 2026 for LecturePilot. Selection: direct tests of tutoring,
independent learning, ordinary deployment, and mastery workflows. These notes
cover four selected studies, not a systematic review or LecturePilot efficacy test.

## Inclusion and access

All four were verified in the map's actual embedded `hoverDataEncoded` dataset,
decoded from [the map HTML](https://ipattis.github.io/SCALE_research/), rather
than inferred from keyword searches. Stanford record slugs:

- Bastani: [`generative-ai-can-harm-learning`](https://scale.stanford.edu/ai/repository/generative-ai-can-harm-learning).
  The index retains the earlier title and SSRN 4895486; the published paper adds
  “without guardrails” and the high-school mathematics subtitle.
- Kestin: [`ai-tutoring-outperforms-class-active-learning-rct-introducing-novel-research-based`](https://scale.stanford.edu/ai/repository/ai-tutoring-outperforms-class-active-learning-rct-introducing-novel-research-based).
- NUMI: [`making-ai-tutoring-productive-evidence-mastery-based-math-practice-experiment`](https://scale.stanford.edu/ai/repository/making-ai-tutoring-productive-evidence-mastery-based-math-practice-experiment).
- Khanmigo: [`one-click-away-ai-tutoring-khanmigo-two-year-school-experiment`](https://scale.stanford.edu/ai/repository/one-click-away-ai-tutoring-khanmigo-two-year-school-experiment).

Read actual PDF methods, results, discussion and relevant tables. Bastani uses
our existing 68-page author PDF archive. The other complete public PDFs and
extracted text are saved in ignored `docs/research/full-texts/scale-2026-10-17/`:
`kestin`, `oreopoulos-mastery`, and `oreopoulos-khanmigo`.
Kestin's separate online supplement was not read; reported supplementary
analyses below are identified as the main article's account. Working papers
may change. We do not rely on the map's AI summaries for findings.

## 1. Bastani et al.: safeguards prevent harm; gains remain unproven

**Citation:** Bastani, H., Bastani, O., Sungu, A., Ge, H., Kabakcı, Ö., &
Mariman, R. (2025). _Generative AI without guardrails can harm learning:
Evidence from high school mathematics._ PNAS, 122(26), e2422633122.
[Published DOI](https://doi.org/10.1073/pnas.2422633122);
[complete author manuscript](https://hamsabastani.github.io/education_llm.pdf).

**Design and measurement:** Nearly 1,000 pupils in one Turkish high school;
grades 9–11; four 90-minute sessions. Class-level assignment with scheduling
constraints; regular-class pupils had been randomly assigned to classrooms.
Each session combined teacher review, practice with textbooks/notes plus
assigned AI access, and a closed-book, closed-laptop immediate exam. Primary
regression excludes honors classes and survey nonresponders; 2,848 student-session
observations, not 2,848 different pupils. Standard errors cluster by class.
See manuscript §§2–3 and Table 1, printed pp. 5–10.

**Intervention:** GPT Base versus GPT Tutor versus no AI. Tutor bundled
hint-first instructions with teacher-supplied solutions, likely mistakes and
feedback. Therefore the experiment does not isolate “Socratic prompting.”

**Results:** Relative to control, assisted scores rose 0.137/1 for Base and
0.361/1 for Tutor: +48%/+127% of the control mean. Immediate unaided exam scores
fell 0.054/1 for Base (SE 0.022, p<.05), about 17% of control performance.
Tutor's estimate was −0.004/1 (SE 0.013), statistically indistinguishable from
control. These are relative changes, not percentage-point learning gains.

**Limits and implication:** No delayed retention test. Students' positive
perceptions diverged from performance. Tutor largely mitigated observed harm;
it did not establish an unaided advantage. For LecturePilot, support exposure
must remain distinct from independent evidence. Reviewed solutions and
misconception-specific help matter alongside refusal to reveal answers.

## 2. Kestin et al.: a strong designed-lesson result, not universal tutoring proof

**Citation:** Kestin, G., Miller, K., Klales, A., Milbourne, T., & Ponti, G.
(2025). _AI tutoring outperforms in-class active learning: an RCT introducing a
novel research-based design in an authentic educational setting._ Scientific
Reports, 15, 17458. [Article](https://doi.org/10.1038/s41598-025-97652-6);
[published PDF](https://www.nature.com/articles/s41598-025-97652-6.pdf).

**Design:** Two-lesson randomized crossover in Harvard introductory physics,
fall 2023. Of 233 enrolled students, 194 were eligible. Existing peer groups
of 2–3 students were randomized together. Topics: surface tension and fluid
flow, one week apart. At-home AI lessons and in-class active learning shared
content and worksheets; prerecorded versus live introductions, individual
AI feedback versus peer/instructor interaction. See pp. 2–3 and 7–8.

**Results:** Pooled reported post-test observations: AI N=142, classroom N=174;
median post-test 4.5 versus 3.5, pooled pre-test median 2.75. The main article
reports adjusted linear-model effect 0.63 SD; ceiling-adjusted quantile
estimates 0.73–1.3 SD, not one uniform effect size. Median AI time was 49
minutes versus an assumed 60 classroom learning minutes. Thus the common
“half the time” headline is not the observed median comparison. See pp. 2–3.

**Mechanism and boundary:** Teachers supplied detailed solutions; software
sequenced problem parts because system prompts alone did not reliably preserve
sequence. Immediate learning improved for this prepared lesson package;
individual ingredients were not randomized. No delayed retention or semester
achievement outcome. Tests were written separately from tutor/lesson design,
but AI condition's home tests lack classroom-equivalent supervision. See pp. 4–8.

**Implication:** LecturePilot should keep sequencing and assessment transitions
in software, and evaluate generated instructional content against expert-written
reference lessons. Professor approval does not show equivalence to expert-built,
question-specific instruction. Do not transfer this study's effect size to our
platform or claim it demonstrates durable learning.

## 3. Oreopoulos et al.: mastery thresholds and learning can separate

**Citation:** Oreopoulos, P., Liut, M., Sungu, A., & Low, N. (2026).
_Making AI Tutoring Productive: Evidence from a Mastery-Based Math Practice
Experiment._ NBER Working Paper 35621, August. **Not peer reviewed.**
[Paper](https://doi.org/10.3386/w35621);
[full PDF](https://www.nber.org/system/files/working_papers/w35621/w35621.pdf).

**Design:** Individual randomization to AI/CAL-only, mastery/non-mastery and
one of two topics. Same NUMI platform, videos, questions, feedback and worked
solutions across AI arms. 6,997 grade 6–8 pupils logged into the first activity;
5,752 returned for a four-question delayed test approximately one week later.
One practice assignment during a normal class in March 2026, one district.
Mastery required one minute of video and three consecutive correct answers;
non-mastery required attempting at least one question. See §§2–3, Tables 1–3.

**Results:** Mastery raised Exercise 1 three-correct attainment 28.7 percentage
points and attempts 4.62, without detectable delayed-learning gains. In the
mastery delayed-test subgroup (N=3,209), AI raised practiced Exercise 1
correctness from .370 to .402: +3.2 percentage points (SE 1.7 points; prose
p=.065). The combined practiced-minus-unpracticed effect was +.026 questions
(SE .034), inconclusive. Table 5's +.085 is a mastery×AI interaction on the
sum of two practiced items; it is not +.085 SD or the average AI treatment effect.
See §§4–5 and Tables 4–5, 9, printed pp. 16–22, 36–42.

**Mechanism and limits:** In observed mastery mistake events, AI improved
next-attempt accuracy 8.5 points, reduced attempts to next correct by .962,
and added 2.876 minutes. Those outcomes condition on treatment-affected
mistakes and later attempts; they are mechanism evidence, not clean overall
causal learning estimates. AI reduced later-content exposure. Four delayed
items, incomplete follow-up and one session limit inference. See Table 8 and §6.1.

**Implication:** Preserve delayed independent checks. Do not equate gate passing,
short correct streaks or more practice with durable understanding. Inspect
post-error learning and lesson coverage together. Changing the gate threshold
alone has weaker support than improving the help students receive after errors.

## 4. Oreopoulos & Low: available tutoring often stays unused

**Citation:** Oreopoulos, P., & Low, N. (2026). _One Click Away: AI Tutoring
with Khanmigo in a Two-Year School Experiment._ NBER Working Paper 35620;
EdWorkingPaper 26-1551, August. **Not peer reviewed.**
[DOI](https://doi.org/10.3386/w35620);
[full author paper through Annenberg](https://edworkingpapers.com/sites/default/files/ai26-1551.pdf).

**Design:** Within-school grade randomization: 53 grade-school clusters,
28 treated/25 control, across 18 Tennessee middle schools in 2024–26. Treatment
was Khan Academy plus Khanmigo during routine 25–40-minute remedial blocks;
control was usual remediation, including other software. Primary estimate:
6,902 student-term observations, not distinct students; yearly endline samples
1,214 and 1,545. Two originally eligible schools were excluded; another closed
before Year 2. See §§2.2–2.3, Tables 5–7, printed pp. 9–13 and 23–28.

**Results:** Pooled assignment effect +1.264 national percentile ranks per
term (SE .597), or +.040 full-population SD (SE .019). Authors summarize annual
gains about .06–.08 SD. The roughly .14 SD estimate scales to full participation;
it is not the randomized intention-to-treat effect. Year-2 engagement analysis
matches 563 treated students. 96% ever messaged Khanmigo; median messaging on
one-third of practice days and 17% of mistake sessions. Only 14.5% of messages
contained a mathematical question or reasoning step. See §§3–4, Appendix A3–A4.

**Critical attribution limit:** There was no randomized Khan Academy-without-AI
arm. Similarity to non-AI platform gains comes from external quasi-experimental
benchmarks. The trial establishes modest effects of the combined program,
not zero causal contribution from AI. Substantive-message classification partly
uses an LLM, and deployment/uptake results need not generalize to voluntary
university use. See introduction and §§3, 5.

**Implication:** A visible Tutor panel and first-use count do not establish
productive tutoring. Test whether learners explain reasoning, obtain useful
help after errors, and return for independent checks. Engagement support is a
hypothesis to evaluate, not proof that mandatory dialogue improves learning.

## Combined interpretation for LecturePilot

These papers favor carefully prepared instruction, software-owned structure,
useful feedback at errors, and independent outcome measures. They do not
establish that AI always adds learning beyond a good non-AI learning workflow.

The highest-value comparison is LecturePilot's complete guided workflow versus
the same published material and practice without conversational AI. Use a
prespecified delayed, unaided assessment with genuinely different cases.
Keep satisfaction, chat use, gate passes, coverage, time and cost as secondary
measures. This is an evaluation proposal, not an implemented experiment.

Code-specific alignment and remaining gaps belong in the companion current-code
comparison. These notes deliberately do not infer deployed behavior from papers.
