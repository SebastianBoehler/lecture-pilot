# Controlled AI-tutoring studies: evidence and implementation

Checked: 2026-09-06. Companion evidence to the El Salvador pilot investigation.
These studies concern different interventions, populations and outcomes; their
effect sizes are not a ranking of models or evidence of LecturePilot efficacy.
This is a research note, not an application implementation or code audit.

## 1. Bastani et al. (PNAS, 2025): assistance is not learning

A Turkish high-school field experiment compared ordinary study resources with
two GPT-4 interfaces across four 90-minute sessions, involving nearly 1,000
students. Both AI arms improved assisted practice: GPT Base by 48% and GPT
Tutor by 127%, relative to control. On subsequent closed-book, closed-laptop
exams, Base reduced grades by 17% (5.4 percentage points). Tutor's effect was
statistically indistinguishable from control: guardrails mitigated harm, but
did **not** establish an unaided-learning gain. Outcomes were short-term.
[Paper and author manuscript](https://hamsabastani.github.io/education_llm.pdf)

Implementation: teachers supplied correct solutions, common errors and
problem-specific hints. The Tutor prompt requested student work before help,
progressively increased assistance, withheld full solutions and asked for
reasoning even after a correct answer. Producing these inputs required teacher
labor; this was not an automatically generated curriculum.
[Methods and example prompts](https://hamsabastani.github.io/education_llm.pdf)

The authors release analysis code, anonymized results and conversation data;
the inspected repository is not a ready-to-deploy tutor application.
[Official repository](https://github.com/obastani/GenAICanHarmLearning)

The August 2025 correction changes an author affiliation following a production
error; it does not revise the reported learning results.
[PNAS correction](https://doi.org/10.1073/pnas.2518204122)

## 2. Kestin et al. (Scientific Reports, 2025): designed university lessons

The trial involved 194 Harvard physics students. Students crossed between an
AI-supported home lesson and an instructor-led active-learning lesson across
two consecutive weeks. The published abstract reports greater learning in
less time and greater reported engagement/motivation with the AI tutor.
[Published study](https://doi.org/10.1038/s41598-025-97652-6),
[accessible publication record](https://pubmed.ncbi.nlm.nih.gov/40537565/)

Implementation was course-specific: instructor-authored, content-rich prompts,
scaffolding, pre-vetted feedback and self-paced interactions through a custom
GPT-API application. The university's account describes pre/post content
tests, not a semester-long retention result. Its 2024 report is preliminary;
use the 2025 paper for formal citation. This supports carefully designed
lessons, not replacement of an entire degree with unrestricted chat.
[Harvard implementation account](https://news.harvard.edu/gazette/story/2024/09/professor-tailored-ai-tutor-to-physics-course-engagement-doubled/)

The verified public repository contains a Stata study-data file, not the
production tutor source. An older v3 repository link returned 404; v4 works.
[Study data v4](https://github.com/HarvardAItutor/Study-Data-v4)
Full-text publisher/PMC retrieval was blocked during this check, so this note
does not independently certify detailed test-access controls or exact timing
and standardized-effect estimates from the full article.

## 3. Wang et al. (Tutor CoPilot): supporting the human tutor

The preregistered study involved approximately 900 tutors and 1,800 K–12
students. Tutors, not students, received AI access. Assignment increased
session exit-ticket passing by four percentage points overall; the lower-rated
tutor subgroup improved by nine points. This is a session-level mastery
measure, not a delayed independent-transfer exam. Human tutoring remained in
both arms. Reported limitations include suggestions inappropriate for grade
level. [Paper, v2](https://arxiv.org/html/2410.03017v2)

Implementation embeds on-demand pedagogical suggestions in a live tutoring
workflow. Tutors can adapt them; examples emphasize guiding questions and
eliciting explanations over giving answers. The reported $20 per tutor/year
is an API-cost extrapolation from $1,419.66 across 429 treatment tutors over
two months; it excludes the cost of employing human tutors and is not a
complete tutoring-service price. [Methods and cost appendix](https://arxiv.org/html/2410.03017v2)

An Apache-2.0 demo notebook and tutorial are public. They illustrate the
approach, not the whole production platform or original experiment.
[Official demo repository](https://github.com/rosewang2008/tutor-copilot/)

## 4. De Simone et al. (World Bank): supported use in Nigerian schools

The six-week English intervention used Microsoft Copilot/GPT-4 in nine public
schools: twelve 90-minute after-school sessions, paired students, contextualized
curriculum-aligned prompts and teacher guidance. Student-level randomization
assigned 657 volunteers to treatment and 671 to control; 759 formed the final
analytical sample. The authors report +0.31 SD on a combined English/AI/digital
assessment, approximately +0.24 SD in English and +0.21 SD on the term exam.
[Authors' methods/results presentation](https://voxdev.org/sites/default/files/2026-03/From%20Chalkboards%20to%20Chatbots.pdf)

Interpretation: this tests an extra, structured learning program against
business-as-usual, not AI against equally intensive non-AI tutoring. Attrition,
volunteer selection, spillovers and infrastructure problems matter. The
authors report attrition sensitivity analyses. The “1.5–2 years” framing is
a benchmark conversion, not observation of two years of durable learning.
API-only costs cannot be compared with the reported $48/pupil pilot cost.
[Authors' presentation, robustness/cost sections](https://voxdev.org/sites/default/files/2026-03/From%20Chalkboards%20to%20Chatbots.pdf)

The implementation used an off-the-shelf interface, not a released custom
tutor codebase. Public implementation guidance describes prompts and teacher
support; no runnable application repository was verified here.
[World Bank implementation account](https://blogs.worldbank.org/en/developmenttalk/addressing-the-learning-crisis-with-generative-ai--lessons-from-)

## LecturePilot implications: proposals, not proven mechanisms

The following are engineering/research inferences from the distinctions above,
not findings that these studies tested in LecturePilot:

1. Keep two separate scoreboards: assisted task completion and an unseen,
   unaided exit task. Add a delayed transfer check when evaluating efficacy.
2. A reusable teaching policy can automate the _structure_, but concept-specific
   correct solutions, misconceptions, evidence and hints still need validation.
   Schema validity does not establish pedagogical or mathematical correctness.
3. Store assessment answer keys/rubrics separately from learner-visible hints.
   Ask for an attempt, diagnose the actual error, give the smallest useful hint,
   then fade help. Do not count a copied correct answer as independent mastery.
4. Evaluate the complete package with a time-matched comparator, predeclared
   outcomes and blinded scoring. Log attrition, failed sessions and assistance.
5. Report both provider cost and total delivery cost, including author review,
   devices, infrastructure and teacher support. Report p50/p95 latency and
   completion failures separately from learning gains.

For a presentation, the defensible synthesis is: purpose-built AI tutoring can
improve measured learning in some settings, but access alone is insufficient;
independent performance, instructional design and implementation context are
central. None of these studies verifies LecturePilot's own effectiveness.
