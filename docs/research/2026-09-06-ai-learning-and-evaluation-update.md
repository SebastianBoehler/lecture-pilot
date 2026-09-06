# AI learning and evaluation: an updated evidence check

Checked 6 September 2026 for the presentation on 7 September. This targeted
review adds recent experiments and evaluation methods to the
[earlier controlled-study note](2026-09-06-ai-tutoring-controlled-studies.md).
Searches used PubMed, arXiv, ACL Anthology, IZA and publisher/author papers.
Working papers, expert-rating benchmarks and learner experiments are distinguished.
No effect below is an estimate of LecturePilot's effectiveness.

## Human learning studies

### Bastani et al., PNAS, 2025

[Original author manuscript](https://hamsabastani.github.io/education_llm.pdf).
See the earlier controlled-study note. The guarded intervention mitigated harm;
it did not establish an unaided benefit or isolate an attempt-first button as its
causal ingredient. Preserve a separate unaided outcome.

### Kestin et al., Scientific Reports, 2025

[Publication record](https://pubmed.ncbi.nlm.nih.gov/40537565/),
[original article](https://doi.org/10.1038/s41598-025-97652-6).
See the earlier controlled-study note. The indexed original reports a median
49-minute AI lesson versus an assumed 60 classroom minutes, not half the time.
Post-lesson performance does not establish semester retention. Publisher/PMC
retrieval was blocked; this pass read the PubMed abstract and indexed original
results, without independently reverifying detailed assessment access controls.

### Contractor & Reyes, IZA Discussion Paper 18792, July 2026

[Original working paper](https://docs.iza.org/dp18792.pdf), Sections 3–5, Table 4.
Of 211 undergraduate participants, 204 attended both sessions. Randomized AI
access while learning unfamiliar topics produced approximately +0.27 SD on both
an immediate knowledge test and a test intended to be unaided one week later. The latter
effect was +5.1 percentage points; different tests and standardizations do not
establish complete retention. Overall essay quality was imprecisely estimated.
Test-rule violations increased by 12.6 percentage points. AI-use styles were
classified from behavior after assignment,
not separately randomized. The paper is preliminary, not a peer-reviewed result.

**Implication:** ordinary AI access can help in some settings. Associations with
explanation-seeking versus delegation do not prove which interaction caused gains.

### LearnLM Team / Google & Eedi, December 2025 preprint

[Original report](https://arxiv.org/html/2512.23633v1), Methods and Appendix F.
The exploratory seven-week study involved 165 pupils aged 13–15 in five UK
schools. Human tutors reviewed every AI message before delivery. Its headline
+5.5 percentage-point estimate versus human tutoring has a 95% credible interval
of −1.4 to +12.4 and concerns the first question on the next topic that same day.
It establishes neither superiority nor seven-week retention. Immediate
AI-versus-human contrasts had intervals spanning zero; the comparison with static
hints was more favorable. Cancelled sessions were recoded as static hints and
transfer required same-day continuation. This is evidence for supervised AI assistance in that
platform, not an autonomous tutor equivalence trial.

**Implication:** human supervision and outcome timing belong in the headline.
Do not transfer an expert's acceptance rate into a claim of autonomous safety.

### Wang et al., Tutor CoPilot, 2024/2025 preprint

[Original report, v2](https://arxiv.org/html/2410.03017v2).
See the earlier controlled-study note. Humans tutored in both groups; AI assisted
the tutor. The exit-ticket result concerns session performance, not delayed transfer
or teacher replacement. Keep that intervention boundary explicit.

### Shen & Tamkin, How AI Impacts Skill Formation, 2026 preprint

[Original study, v2](https://arxiv.org/html/2601.20245v2).
The main randomized study had 52 Python-experienced participants learning the
unfamiliar Trio library. AI assistance reduced performance on the ensuing
conceptual, code-reading and debugging assessment; average time savings were
not statistically significant. This was a short, speed-oriented coding task,
not a delayed university-course experiment. Described interaction styles were
observed rather than assigned interventions.

**Implication:** successful code generation is distinct from understanding and
debugging. For programming goals, assess tracing, explanation and error diagnosis.

## Evaluating a tutor is different from evaluating learning

### Maurya et al., MRBench, NAACL 2025

[Original peer-reviewed paper](https://aclanthology.org/2025.naacl-long.57.pdf).
MRBench contains 192 mathematical conversations and 1,596 tutor responses with
human annotations across eight dimensions, including mistake identification,
location, guidance and answer revelation. It also evaluates LLM judges against
human ratings. These are judgments about tutoring responses, not experimental
student learning gains. The taxonomy is useful for a diagnostic audit; dimensions
such as human-likeness need not become LecturePilot optimization targets.

### Macina et al., MathTutorBench, EMNLP 2025

[Original peer-reviewed paper](https://aclanthology.org/2025.emnlp-main.11.pdf).
The benchmark separates subject expertise, understanding student errors and
pedagogical behavior. Strong solving ability did not automatically yield good
tutoring, and longer dialogues challenged simple questioning strategies. Its
reward-model and dialogue evaluations do not establish delayed human transfer.
Use process metrics to find defects, retaining separately scored learner outcomes.

The same boundary applies to simulated students: the existing
[StudentSim review](2026-09-03-studentsim.md) and
[ETQ-AI review](2026-09-03-etq-ai.md) propose offline diagnostics. This block did
not re-audit those complete releases. Simulator improvement or agreement with
teaching ratings must not be presented as LecturePilot learning efficacy.

## A relevant laptop finding, without a device prescription

Urry et al. (2021), _Psychological Science_,
[original replication](https://doi.org/10.1177/0956797620965541),
[full paper inspected](https://static1.squarespace.com/static/587ea259197aea1c1d66ec5b/t/601f2ac8268c6a7b9735c877/1612655305004/urryetal_psci_2021.pdf).
The randomized replication analyzed 142 of 145 university participants. It did
not reproduce an immediate quiz advantage for longhand over laptop notes after
roughly a 30-minute delay without note review. Typed notes contained more words
and more verbatim text. Neither this result nor the original experiment settles
long-term note-review benefits, accessibility or digital distraction. Correlations
between note content and scores are not randomized tests of note-taking strategy.

**Implication:** avoid a blanket handwriting or device mandate. Offer a legible,
stable workspace and assess what the student can explain or do with the material.

## Current-code evidence and a bounded robustness improvement

Inspected at commit `cb4f771`: `model_client.py`, `model_commands.py`,
`coaching_transitions.py`, `coaching_support.py`, `assessment_feedback.py`, and
`scripts/benchmark_gate_models.py`.

- The runtime already has structured assessment, backend-derived pass status,
  professor-owned rubrics, separate support records and reviewed task identities.
- The UI qualifies independence as “in this app.” Closing local teaching and
  recording local help does not verify that a learner used no external assistance.
  An efficacy study needs a defined assessment-access protocol.
- Post-assessment support selects the next unexposed approved hint; explicit
  help starts with the first approved hint. Neither selector uses the particular
  missing evidence IDs. This is bounded approved support, not full
  misconception-specific adaptation.
- The six legacy benchmark scenarios use general turns. A read-only construction
  check found `checkpoint_assessment_required=False` and `pending_check_task_id=None`
  for every scenario. They still use shared model infrastructure, but omit the
  explicit checkpoint requirement and issued-task binding in the new workflow.
  This is a verification gap, not proof of a learner-runtime defect.

Recommended final hardening: exercise the exact checkpoint path and reviewed
task snapshot, then evaluate both evidence decisions and the persisted transition.
Include a valid paraphrase, correct result with wrong reasoning, correct reasoning
with an arithmetic error, explicit uncertainty, a misleading keyword-rich answer,
help followed by success, a changed task, and a stale submission. Labels must be
reviewed against the particular rubric; no generic rule may silently change it.
Report false passes, false rejections, missing-criterion decisions and contract
failures separately. A small regression set is a release check, not a population
accuracy estimate. No new provider benchmark was run in this research block.

The read-only benchmark construction check can be reproduced from the repo root:

```bash
.venv/bin/python - <<'PY'
import runpy
from lecturepilot.model_commands import checkpoint_assessment_required

benchmark = runpy.run_path("scripts/benchmark_gate_models.py")
build_turn = benchmark["_turn_for_scenario"]
for scenario in benchmark["SCENARIOS"]:
    turn = build_turn(scenario)
    print(scenario.label, checkpoint_assessment_required(turn),
          turn.coaching_context.pending_check_task_id)
PY
```

At the inspected revision, every row printed `False None`. Existing explicit
checkpoint contract tests are in `apps/api/tests/test_checkpoint_model_request.py`;
they set the checkpoint identity and check the single structured call without tools.
The benchmark omission does not mean those production contract tests are absent.

## What this supports for tomorrow

The defensible claim is that LecturePilot implements an inspectable, source-bound
learning workflow informed by research. Evidence remains mixed across AI systems,
tasks and populations. The next substantive scientific test is independent,
delayed application with an appropriate comparator and human-calibrated scoring.
Add no claim of proven efficacy, universal personalization or neuroadaptation.
