# SCALE: feedback and assessment paper notes

Read on 17 October 2026. These are complementary primary-source notes for the
LecturePilot comparison, not evidence that LecturePilot improves learning.

## Selection and access

All three titles occur in the embedded paper records of the
[SCALE map evidence page](https://ipattis.github.io/SCALE_research/evidence.html),
the 10 October 2026 snapshot. Exact record IDs:

- `tutor-copilot-human-ai-approach-scaling-real-time-expertise`
- `making-ai-generated-feedback-matter-large-scale-study-feedback-workflows-and-student`
- `llm-judge-validity-physics-assessment-depends-more-task-model`

The physics paper also has an earlier-title/version duplicate; count it once.
The map is discovery evidence only. Results below come from actual full texts:
methods, result tables, discussion and limitations. PDFs are archived privately
under `docs/research/full-texts/scale-2026-10-17/` (gitignored).

## Tutor CoPilot: A Human-AI Approach for Scaling Real-Time Expertise

[Wang et al., November 2025 PDF](https://edworkingpapers.com/sites/default/files/ai24_1054_v2.pdf).
Read pp. 2–12 and supplementary endpoint analysis.

Randomized tutor access versus ordinary human tutoring; 783 active tutors,
1,013 grade 3–6 students, 4,136 sessions over about seven weeks. Humans selected
and edited AI suggestions. Unconditional exit-ticket passing increased
4.0 percentage points (SE 1.5; adjusted p=.010), from a 61.7% control mean.
Conditional passing increased 3.1 points (SE 1.4; adjusted p=.040).
Lower-rated tutors' students gained about nine points.

**Critical limitation:** initial preregistered outcome was end-of-year MAP math
achievement; analysis shifted to session outcomes because mixed tutor assignment
produced weak sustained exposure. End-of-year differences were not significant.
The bundle does not identify which teaching strategy caused improvement.
This is human-mediated K–12 evidence, not an autonomous university tutor trial.

**Implication to test:** specific probing and error remediation are promising;
retain professor judgement over authored teaching and distinguish immediate
checkpoint success from delayed independent learning. Human review at authoring
time is a different intervention from a human choosing each live response.

## Making AI-Generated Feedback Matter

[Alsaiari et al., arXiv:2608.11625v2](https://arxiv.org/html/2608.11625v2).
Read §§3–5, especially §§3.2, 3.4.1 and Tables 2–5. Preprint.

Sequential cohorts: 13,037 students, 51,296 authored resources, 70 course
offerings. Compared static comments, optional dialogue, and a workflow selecting
suggestions before targeted dialogue. Estimated downstream editing was 26.2%
for the structured workflow versus 14.1% for static feedback: +12.1 points
(simultaneous 95% CI 10.7–13.5). Peer-rated submitted quality improved by
0.137 on a 0–5 scale (CI .116–.158).

**Critical limitations:** no randomization; semesters/cohorts differed; the
structured cohort used GPT-5 mini, others GPT-4o mini. Editing definitions also
differed by workflow and did not establish correct incorporation of suggestions.
Median revisions were zero in every cohort. Quality meant peer moderation,
not an independent retention or transfer test. Treat associations as hypotheses.

**Implication to test:** after assessment, ask the learner to select a correction,
explain why, then apply it. Measure the resulting independent answer, rather
than counting displayed comments or chat length as learning.

## LLM-as-a-judge validity in physics assessment depends more on the task than the model

[Yeadon et al., arXiv:2603.14732v2](https://arxiv.org/html/2603.14732v2).
Read §§III–VI and result tables. Preprint; not a learning intervention.

Compared five models against human marking on 771 university exam items,
1,151 curriculum questions, 55 essay scripts (275 essays), and 1,400 plots.
Structured-item rank correlations exceeded .6; plots exceeded .84. Essay
rank agreement remained near zero despite exemplars making mean scores look
more human. False reference solutions harmed absolute grading accuracy.

**Critical limitations:** structured responses were AI-generated, not actual
student answers. Essay human agreement was itself very poor: mean pairwise
rho=.054; single-rater ICC=.035 (95% CI −.01 to .11). Plot evaluation included
preceding notebook context, not arbitrary visual reasoning. Task format is
confounded with authorship and marking context. This cannot establish that
all essay assessment fails or that structured checkpoints are accurate enough.

**Implication to test:** calibrate each checkpoint family against independently
judged real learner responses, including partial misconceptions. Check false
passes and false failures separately. Professor-approved reference material
still needs correctness checks; schema validity and plausible feedback do not
demonstrate semantic grading validity.

## Excluded candidate

The ICER 2026 study _Steering AI Tutors Through System Prompts_ (N=1,059)
is relevant external context, but an exact-title/author search did not establish
its inclusion in this map snapshot. It is excluded from this selection.

## Comparison boundary

These notes deliberately do not infer current LecturePilot behavior from its
design instructions. The companion synthesis must cite inspected implementation
paths before calling a mechanism implemented, missing, or validated.
