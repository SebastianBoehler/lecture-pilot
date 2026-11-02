# &Tutor, Persimmon and TutorMoments: evidence and implications for LecturePilot

Research note, 2026-11-02. Prompted by an X thread from the StudentSim first
author that quoted the humans& launch of Ampersand Tutor (&Tutor) on 30 October 2026. Sources: the &Tutor launch post and model card, the Persimmon v0.1 model
card, the &Tutor API documentation, and the TutorMoments-Preview working paper.
The headline numbers below were checked against the launch post's HTML. No
independent replication exists. The StudentSim status update is at the end;
the main StudentSim analysis is in
[2026-09-03-studentsim.md](2026-09-03-studentsim.md).

## Bottom line

&Tutor is the second "train the tutor against a learner simulator" result
after StudentSim, and the first with a commercial API. It moves from chess to
open-ended maths dialogue, but it shares StudentSim's central gap: **no real
student was taught**. The headline "best on a widely-used tutor eval" means
the highest TutorMoments score **under a minimal prompt**. TutorMoments
scores, by LLM judge, whether a tutor scaffolds or pushes for rigor at
teacher-flagged moments in 5-turn replays. It does not measure learning.

With TutorMoments' evaluation-aware prompt, which spells out the
support-versus-rigor trade-off, &Tutor (0.919) is roughly level with GPT-6
Astra (0.926) and Claude Sonnet 5.5 (0.902). The untrained GLM-5.3 base
reaches 0.877. Most of the plain-prompt advantage is therefore the kind of
behaviour that explicit pedagogical instructions already produce in frontier
models. LecturePilot already gives such instructions through its
backend-derived scaffold policy. The interesting residual is **appropriate
rigor**, where &Tutor still leads (0.931).

The most useful finding for LecturePilot is the learner ablation. The same
recipe trained against GLM-5.3 as the learner instead of Persimmon scores far
lower (0.635 vs 0.754 at max reasoning, 0.477 vs 0.659 at low). This is
the strongest evidence so far that simulator quality, not RL alone, drives
these gains. It still shows only that a better simulator yields better
simulated-benchmark behaviour.

Sources: [&Tutor launch post](https://tutor.humansand.ai/blog/),
[&Tutor model card](https://tutor.humansand.ai/blog/model-card),
[Persimmon v0.1 model card](https://persimmon.humansand.ai/blog/persimmon-model-card.html),
[API docs, tutor model](https://ampersand.humansand.ai/docs/#tutor-model),
[TutorMoments-Preview paper](https://tutormoments.allen.ai/static/paper/tutormoments-preview.pdf).

## What humans& built

- **Persimmon v0.1** (released 10 September 2026, research preview) is a
  "user model" that simulates how people respond in conversation. It is
  initialised from NVIDIA Nemotron-3-Ultra-550B-A55B and mid-trained on
  unnamed "diverse chat and forum data". The model card does not claim that
  it models knowledge change over time. Its long-horizon tests measure
  conversational behaviour: information "trickle" and coherence at 80 turns.
- **&Tutor** (`ampersand-tutor-v0.1`, 30 October 2026) is GLM-5.3 trained
  with RL in simulated tutoring conversations. Persimmon plays the learner and
  "a judge evaluates a student's learning". The post says the tutor is
  rewarded "by how much the student learns". It discloses neither the
  algorithm, nor the reward definition, nor how learning is measured inside an
  episode. Authors: Alexis Ross and Manya Bansal (equal contribution) "&
  friends at humans&".
- **Learner validation** compares Persimmon with real learners on four maths
  datasets (SimulatorArena Math, StudentBench GRE sessions, Eedi,
  TutorMoments). It looks at the distribution of conversational moves, affect
  and error rates, coded by LLMs with held-out Fleiss' κ of 0.696–0.840.
  Real learners are wrong on 25–30% of checkable claims, Persimmon on 19–33%,
  and other models on 15% or fewer. In the multi-user Turing test, an LLM
  judge mistakes Persimmon for a human 19.8% of the time on TutorMoments,
  where 50% would mean indistinguishable.

## What TutorMoments measures

TutorMoments-Preview (Zhang, Ross, … Andreas, Loeb, Lo, Knight; AI2, MIT,
Stanford and others) is a preliminary working paper. It releases 462
de-identified transcripts of 198 US students in grades 2–7 with 173 volunteer
tutors, almost all in maths, and more than 1,500 teacher-annotated key
moments.

- Experienced maths teachers mark moments where a tutor should scaffold or
  push for rigor. When several teachers annotated the same moment, all agreed
  on scaffolding-appropriateness in 68% of cases and on rigor in 63%.
- An LM tutor continues the real transcript from the cut point for 5 turns
  (3 tutor, 2 student). The student is a Claude Opus 4.6 "oracle student"
  that sees the full original transcript. The authors observed that even
  this student produces "unnaturally successful learning behaviors", and they
  call it a placeholder.
- An LLM pipeline describes and classifies the tutor's actions. Metrics:
  scaffolds in scaffolding moments, pushes rigor in rigor moments, and avoids
  over-scaffolding.
- The authors' own finding: minimally prompted frontier models over-scaffold
  and rarely push for rigor (GPT-5.5 does so in 4.6% of rigor moments).
  Evaluation-aware prompts help substantially.
- Stated limitation: the authors "have not yet examined whether tutors who
  adapt … actually yield improvements in real students' learning".

## Reported &Tutor results (TutorMoments overall, higher is better)

| Model (reasoning)              | Plain prompt | Evaluation-aware |
| ------------------------------ | ------------ | ---------------- |
| &Tutor (max)                   | **0.754**    | 0.919            |
| Claude Sonnet 5.5 (low effort) | 0.667        | 0.902            |
| &Tutor trained vs GLM-5.3      | 0.635        | 0.883            |
| GPT-6 Astra (high)             | 0.634        | **0.926**        |
| Claude Opus 5.5 (high effort)  | 0.512        | 0.883            |
| GLM-5.3 base (max)             | 0.500        | 0.877            |

On appropriate rigor alone, &Tutor leads under both prompts: 0.577 vs 0.408
for Sonnet 5.5 with the plain prompt, and 0.931 vs 0.915 for GPT-6 Astra with
the evaluation-aware prompt. Under the evaluation-aware prompt it is not top
on scaffolding.

## Limits

- **No learning outcome.** Training reward, benchmark and learner validation
  are all simulated or LLM-judged. The model card states that results "may
  not generalize to human learners, other subjects or longer interactions".
  humans& itself names simulator exploitation as the risk.
- **Independence.** The &Tutor lead author co-authored TutorMoments.
  Persimmon was validated partly on TutorMoments transcripts. The post does
  not say whether those transcripts informed training or checkpoint
  selection, or which student simulator ran the benchmark replays.
- **No uncertainty reported.** The post reports point estimates only, with no
  intervals or repeated runs. The benchmark's own teacher agreement is
  moderate.
- **Domain.** The results cover primary and middle-school maths, competition
  maths and GRE prep. They say nothing yet about university lecture material.
- **API shape.** The tutor model rejects tools and images with HTTP 400. It
  runs in a stateful hosted session with summarisation, and the docs give no
  structured output, data retention or region information.

## Implications for LecturePilot

### Adopt now

1. **Keep explicit pedagogy in the prompt.** TutorMoments shows the largest
   cheap gain comes from stating the support-versus-rigor trade-off.
   `tutor_prompt.py` already requires "the least support that can unlock
   progress". `learner/scaffold_policy.py` derives
   challenge/transfer/worked-step moves from evidence. This is the
   "evaluation-aware" condition, so there is no reason to switch to a
   specialised tutor model on this evidence.
2. **Watch rigor, not just over-help.** Our policy is largely phrased as
   "do not reveal" or "do not solve". The residual gap on the benchmark is
   failing to raise demand when the learner is ready: self-explanation,
   generalisation, harder variants. Check that the `passed` / transfer
   branches actually produce rigor pushes in practice.

### Research before productization

1. **Replay-based tutor evaluation.** TutorMoments' design is directly
   reusable as an offline instrument: cut a real transcript at an annotated
   decision point and compare tutor variants from the same state. The design
   pairs with StudentSim's F/R decomposition and LecturePilot's
   delayed-transfer contract. Build it from consented or synthetic
   university-course sessions, with professor-annotated moments.
   TutorMoments-Preview itself (grades 2–7 maths) is only a smoke test.
2. **Score policy compliance separately from learning.** An LLM classifier
   can check whether a turn followed the active scaffold policy (move made,
   forbidden move avoided). Keep this as a diagnostic, never as learning
   evidence or a gate input.

### Do not import

- Do not route learner turns to `ampersand-tutor-v0.1`. It cannot call our
  typed canvas, workspace or memory tools. It holds conversation state in a
  third-party session outside our harness. It has undocumented data handling
  and maths-only evidence. Sending learner text there would also need new
  privacy disclosures.
- Do not treat a simulator-trained or simulator-scored tutor as evidence of
  learning. As with StudentSim, delayed unaided transfer stays the authority.

## StudentSim status update (2 November 2026)

- The first author's X post claims StudentSim was "#1 HF Paper of the Day",
  a NeurIPS '26 UserSim Spotlight and featured by Microsoft Research. UserSim
  is a NeurIPS 2026 workshop, so a spotlight there is not main-track peer
  review. The Microsoft Research publication page still lists arXiv only, and
  no workshop accepted-papers list was found to confirm the spotlight.
- Since the 3 September note the official repository has one new commit,
  `73005fd` (21 September, an Azure OpenAI fix for GPT-5 deployments). The
  chess data README still says the upload "has not landed yet". The
  reproducibility caveats in the original note stand.
