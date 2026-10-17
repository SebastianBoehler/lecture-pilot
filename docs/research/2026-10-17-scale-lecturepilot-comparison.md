# SCALE papers compared with current LecturePilot

17 October 2026. Seven papers selected from the SCALE map for direct relevance
to tutoring, independent learning, feedback, authoring and assessment validity.
We read their full-text methods, results, relevant tables and limitations.
This is a targeted review, not a systematic review or a product efficacy study.

Current-code comparison: checkout `0f73ec73d64454d17a5840df3cbd5f734bd507b0`,
with local research documentation changes. No product code was changed.
Source inspection and narrow regression tests establish local behavior only;
they do not establish production behavior or learning gains.

Implementation follow-up, 17 October: delayed reviews now require reviewed
practice targets. Generic checkpoints remain immediate practice. The registered
storage migration retires their old queued/pending delayed checks without
rewriting publications. The findings below describe the pre-fix snapshot.

## Main judgment

LecturePilot's reviewed practice flow fits the evidence better than measuring
assisted exercise completion alone: diagnostic attempt, selected help, fresh
independent exit, and later review. Software controls those transitions.
However, the papers do not validate our generated tasks, rubric judgments,
hint quality or learning outcomes. Our highest-value next work is to validate
those components and the complete learning workflow, rather than add more
pedagogical instructions to the tutor prompt.

One concrete gap matters now: the generic checkpoint path does not instantiate
a changed delayed task. It prefixes the original prompt with a request to apply
the reasoning to a changed case. That is materially weaker than the explicit
changed tasks in reviewed practice targets.

## Why these seven papers

Four studies directly examine student tutoring and outcomes, including positive,
negative and mixed findings. Three complementary papers address human-mediated
tutoring, feedback use, and university assessment validity. We prioritized
mechanism and comparison relevance over citation counts or positive headlines.
The selection includes K–12 studies whose product mechanisms may be relevant,
but whose effect sizes cannot be assumed for university learners.

All seven were verified in the map's embedded records. Earlier titles and
duplicate versions were resolved rather than counted as additional studies.
Exact records, samples, estimates, access scope and limitations are in the
[tutoring reading notes](2026-10-17-scale-tutoring-paper-notes.md) and
[feedback/assessment reading notes](2026-10-17-scale-feedback-paper-notes.md).
Full texts are archived locally under ignored `docs/research/full-texts/`.

| Selected paper                                                                                                                                               | Finding that affects our decision                                                                                                                                                                                                                                                                                    | Comparison with LecturePilot                                                                                                                                                                                                                                   |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Bastani et al., PNAS 2025](https://doi.org/10.1073/pnas.2422633122), _Generative AI without guardrails can harm learning_                                   | Unrestricted AI raised assisted practice scores but reduced immediate unaided scores by about 17% relative to control. Guarded tutoring removed most of the harm without demonstrating an unaided gain.                                                                                                              | Keep assisted and independent evidence separate. Our reviewed hint ladder and fresh exit fit this risk. Refusing answers alone is insufficient; the tested tutor also had teacher-prepared solutions and misconception support.                                |
| [Oreopoulos et al., 2026](https://doi.org/10.3386/w35621), _Making AI Tutoring Productive_                                                                   | In 6,997 middle-school pupils, mastery thresholds raised practice success without detectable delayed gains by themselves. AI plus mastery yielded limited, uncertain delayed evidence: +3.2 percentage points on the first practiced item, p=.065; the combined practiced-minus-unpracticed result was inconclusive. | Preserve delayed independent measures and error-specific help. Do not turn gate passes, repeated attempts or correct streaks into claims of durable learning. This working paper does not justify stronger progression locks.                                  |
| [Kestin et al., Scientific Reports 2025](https://doi.org/10.1038/s41598-025-97652-6), _AI tutoring outperforms in-class active learning_                     | A two-lesson university physics crossover found large immediate gains from expert-built AI lessons. Software sequenced problem parts because prompts alone were unreliable. No delayed retention result.                                                                                                             | Our software-owned assessment transitions align. AI-generated teaching plus professor publication is not automatically equivalent to the expert-written, tested lesson package. Compare instructional quality directly before borrowing the result.            |
| [Oreopoulos & Low, 2026](https://doi.org/10.3386/w35620), _One Click Away_                                                                                   | A two-year, 18-school trial found modest combined-program effects. Median students messaged Khanmigo in only 17% of mistake sessions. No randomized Khan Academy-without-AI arm isolated AI's contribution.                                                                                                          | A Tutor panel or first-use count cannot establish productive use. Our automatic post-error support helps make feedback available; whether learners use it and return independently remains unmeasured. This working paper does not prove mandatory chat helps. |
| [Wang et al., November 2025 version](https://edworkingpapers.com/sites/default/files/ai24_1054_v2.pdf), _Tutor CoPilot_                                      | Human tutors with AI suggestions raised session exit-ticket passing by four percentage points. The initial end-of-year outcome shifted to session outcomes; no significant end-of-year improvement was found.                                                                                                        | Supports investigating specific probing and error repair. Humans selected live suggestions; our professor review occurs before the learner session. These are different interventions.                                                                         |
| [Alsaiari et al., 2026 preprint](https://arxiv.org/html/2608.11625v2), _Making AI-Generated Feedback Matter_                                                 | In sequential cohorts of 13,037 students, structured feedback selection and dialogue correlated with more editing and slightly better peer-rated artifacts. Cohort, model and editing-definition differences limit attribution.                                                                                      | Displaying missing criteria is only the start. Test whether learners act on a correction and improve a later independent answer. Editing, dialogue and satisfaction are process measures, not transfer evidence.                                               |
| [Yeadon et al., 2026 preprint](https://arxiv.org/html/2603.14732v2), _LLM-as-a-judge validity in physics assessment depends more on the task than the model_ | Structured-task and contextual plot rankings agreed more with human scoring than essay rankings. Structured responses were synthetic; human essay agreement was itself very poor.                                                                                                                                    | Calibrate by checkpoint family, subject and language. Exact quotations and valid schemas do not establish that the model credited the correct reasoning. The paper cannot certify our open answers or imply all essay grading fails.                           |

## What the current code actually establishes

### Reviewed practice targets have the intended separation

[`learning_map.py`](../../apps/api/src/lecturepilot/learning_design/learning_map.py)
copies reviewed baseline, independent exit, delayed task, hints and supplemental
tasks into `practice-*` gates. In
[`coaching_transitions.py`](../../apps/api/src/lecturepilot/learner/coaching_transitions.py),
diagnostic success still requires an independent exit. Supported success uses a
fresh unexposed reviewed task; exhaustion stays explicit. A diagnostic or
supported response cannot simply become independent evidence.

After failure, hint selection matches missing rubric evidence where bindings
exist and does not substitute unrelated bound hints. However, explicit help
before an assessed answer selects the first approved hint in
[`coaching_support.py`](../../apps/api/src/lecturepilot/learner/coaching_support.py).
We should not describe every help request as misconception-targeted adaptation.
No paper here establishes the effectiveness of our exact selection policy.

### Independent checks have real application controls

[`LessonWorkspace.tsx`](../../apps/web/src/lesson/LessonWorkspace.tsx) waits for
revision-matched learner state and replaces teaching with the focused task.
It closes chat, files and outline during focus.
[`independent_attempt.py`](../../apps/api/src/lecturepilot/learner/independent_attempt.py)
also rejects chat requests during independent and delayed checks. Help requests
persist the support transition before revealing the hint.

These controls make assistance inside the application observable. They do not
rule out outside help, remembered examples or use of another device. An app
record labelled independent is not equivalent to a supervised research test.

### Generic checkpoints have a weaker assessment contract

In `learning_map.py`, `_generic_checkpoint_gate` uses the prompt itself as its
single evidence criterion. It creates a delayed prompt by adding
“Apply the same reasoning to a changed case:” before the original question.
It supplies no concrete new instance. Generic gates start at independent exit,
without the reviewed diagnostic/task-bank design.

Therefore “all checkpoints measure delayed transfer” would be inaccurate.
Review those generic tasks and distinguish their evidence before using course
aggregates to claim transfer. A genuinely changed question still needs equivalent
difficulty, rubric coverage and source support; changing text alone is insufficient.

### Scoring is constrained, but semantic accuracy remains an empirical question

[`checkpoint_assessment_prompt.py`](../../apps/api/src/lecturepilot/learner/checkpoint_assessment_prompt.py)
isolates the issued answer, task, rubric and bounded teaching excerpt. It excludes
chat history, learner memory and future tasks. Claimed criteria need verbatim
answer anchors, checked by
[`checkpoint_evidence_audit.py`](../../apps/api/src/lecturepilot/learner/checkpoint_evidence_audit.py).
These checks verify the quotation exists, not that it proves the criterion.

[`calibrate_gate_assessments.py`](../../scripts/calibrate_gate_assessments.py)
already accepts two human ratings plus adjudicated labels. We found tooling and
the documented ten-case synthetic benchmark, not evidence of completed genuine
learner calibration in the inspected artifacts. Its earlier 10/10 result must
not be presented as current-model or population accuracy. Assess false passes,
false rejections and criterion errors, and rate feedback usefulness separately.

### Later reviews and analytics support evaluation, not a causal conclusion

[`coaching_review_schedule.py`](../../apps/api/src/lecturepilot/learner/coaching_review_schedule.py)
uses fresh tasks for later reviews and expands intervals after success.
[`coaching_goal_evidence.py`](../../apps/api/src/lecturepilot/learner/coaching_goal_evidence.py)
clears current independent/delayed evidence after an independent failure while
retaining history. The selected studies do not validate our interval rule.

[`analytics_outcomes.py`](../../apps/api/src/lecturepilot/analytics/analytics_outcomes.py)
keeps supported, independent and delayed categories separate. These rates
describe observed attempts. They cannot estimate an effect without a comparison
and follow-up denominator. The
[evaluation contract](../evaluation-contract.md) already specifies delayed
independent changed-task performance and missing follow-up, while explicitly
excluding an implemented randomized study or research export.

## Recommended order of work

These are proposals from this review; none were implemented.

1. **Validate task and scoring quality first.** Sample reviewed and generic
   checkpoints across subjects and German/English. Have qualified reviewers
   independently solve tasks, check reference correctness, and judge real
   de-identified or consented answers. Inspect adjudication disagreements rather
   than assuming human labels are automatically reliable. Prioritize generic
   delayed tasks that currently lack an instantiated changed case.
2. **Evaluate feedback through the next learner action.** Check diagnosis,
   actionability and leakage into fresh tasks. Compare whether the next
   independent answer improves. Track burden and coverage too: slower work and
   fewer completed topics can accompany more useful error correction.
3. **Compare the complete workflow with a credible baseline.** A proposed study
   should compare LecturePilot against the same published material and practice
   without conversational AI, with equivalent study opportunity. Use a common
   delayed, unaided changed-task assessment, scored independently of the tutor.
   This estimates the complete workflow effect; a separate, narrower comparison
   would be required to isolate one hint policy. Specify attrition and analysis
   before collection under a separately approved study protocol.

Keep short-term accuracy, engagement, time, coverage and cost as separate
secondary outcomes. Do not add mandatory dialogue, arbitrary mastery thresholds,
extra model reviewers or autonomous task generation from these results alone.

## Verification and limits

- 23 backend tests passed for coaching transitions, targeted hints, reviewed
  task banks, isolated assessment prompts and quotation audit.
- Eight backend tests passed for review scheduling, help routes and exhaustion.
- One frontend test passed for the focused checkpoint interaction.
- These were local deterministic regression checks. No paid model calls,
  live learner sessions, production checks or efficacy experiment were run.

The September audit remains historical. This review refreshes selected behavior
against current source and adds four newly selected papers: the two Oreopoulos
studies, feedback workflows and physics judge validity. Bastani, Kestin and
Tutor CoPilot were already in our bibliography; reading them here is not new
independent replication.
