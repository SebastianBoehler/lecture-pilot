# LecturePilot presentation rehearsal

Draft for Monday, 7 September 2026, based on the student's description of a
nine-ECTS project. Working format: 10 minutes in English, including a two-minute
demo. Adjust timing/language when the presentation requirements are confirmed.
This is optional talk content only. The presenter will design and create the
slides; do not treat any generated deck as the intended presentation.

## Thesis to remember

“The contribution is not another chatbot. It is a source-controlled learning
environment that makes learner attempts, assistance and later independent
performance distinguishable.”

## Seven slides / ten minutes

1. **Problem and scope — 45 seconds.** A helpful-looking answer is not a
   demonstration of learning. Show the two constraints: university-controlled
   course material, and observable student reasoning. Define the project as
   design/engineering plus an evaluation contract, not a completed efficacy trial.
2. **Learning loop — 75 seconds.** Diagnostic attempt → targeted support →
   independent exit → delayed changed-form check. Distinguish novice instruction
   from simply withholding help. Cite retrieval, spacing and feedback research
   from the [science brief](2026-09-04-learning-science-presentation-brief.md).
3. **What changed through feedback — 90 seconds.** June prototype; June 17
   professor feedback; July 2 embedded quizzes/slides/readiness; July 26 factual
   quality failures; August revision-bound attempts and practice design.
   Use the [retrospective](2026-09-04-project-retrospective.md). Show one failure
   and its correction, not a wall of commit counts. Date feedback and code separately.
4. **Architecture — 90 seconds.** Shared authorized course sources, professor
   design approval, validated generation, explicit publication, learner overlays,
   typed backend tools and categorical outcomes. Explain why backend authority
   matters even when prompts are excellent. Conversion is isolated; no model or
   source copy is required per student. External inference is still real compute.
5. **Demo — 120 seconds.** Follow the script below only after its readiness gate
   passes. Show the learning interaction, not upload progress or a long generation.
6. **Evidence and limitations — 90 seconds.** Tests verify contracts; citations
   motivate design; neither proves student benefit. Present the measured startup
   reduction as a build result, not total cost savings. Local read-load results
   are a limited smoke check, not university capacity. Explicitly mention the
   persisted-state issue and recovery work if still unresolved.
7. **Next research question — 90 seconds.** Can source-grounded, assistance-fading
   support improve delayed unaided changed-form performance over a comparable
   source canvas? Specify a future consented protocol, equivalent tasks, missing
   follow-up reporting and revision-compatible outcomes. Close on what the system
   now enables us to test, not an effect we have not measured.

## Two-minute demo script

Preflight: use the exact local/deployed revision rehearsed; confirm the intended
account and published lecture. Do not enter real university credentials on a
projector. Do not reset personal progress or publish new material while presenting.

- **0:00–0:20:** Show the professor workflow and where sources, task design and
  publication approval sit. Use existing approved material; do not start generation.
- **0:20–0:40:** Switch to the prepared learner workspace. Explain the one
  recommended study action; open a previously unlocked lecture.
- **0:40–1:00:** Point to an original slide and open its source in-app. Explain
  that provenance makes claims inspectable but does not guarantee correctness.
- **1:00–1:35:** Submit a prepared, genuinely incomplete checkpoint attempt.
  Show the actual targeted feedback and a correction. Do not substitute a canned
  response for a failed provider call or call a supported answer independent mastery.
- **1:35–2:00:** Show the independent next check/progress state if observed in
  rehearsal. Explain the later transfer check; do not manipulate the clock or
  imply that waiting a few seconds is delayed learning evidence.

Current gate: local lecture version 2 passed factual review after manual source
corrections and was published through the normal approval endpoint. All three
practice targets completed changed-form independent tasks in the browser, with
seven-day reviews scheduled. Pending questions now survive refresh in the canvas.
See the [rehearsal results](2026-09-04-demo-rehearsal-results.md) for the precise
scope, measured latency, backups, and remaining limitations.

## Likely questions and concise answers

**Why not just ChatGPT with the slides?** The research object is controlled
source access, teacher-approved tasks, learner attempts and assistance history.
A model prompt alone does not provide those enforceable state boundaries.

**Where is the scientific evidence?** General retrieval, spacing and feedback
evidence motivates the choices. Tübingen's Wagner et al. study informs feedback
design; ETQ-AI is relevant to teaching-process review, not proof of this tutor's
efficacy. The product needs its own learner evaluation.

**What was your contribution?** State your actual role in problem framing,
feedback interpretation, architecture, implementation/review and verification.
Identify AI-assisted coding honestly. Do not imply sole authorship of collaborators'
commits or attribute every subsequent design choice directly to the supervisor.

**Does deliberate practice explain the whole design?** It motivates explicit
targets, focused attempts and feedback. Use “deliberate-practice-inspired”; the
label itself does not establish the necessary instructional quality.

**Can the university run it cheaply?** Resource-capped local tests handled 30
authenticated active readers at about 14.6 reads/s, zero errors and p95 below
160 ms. That excludes inference and the authoring services; it is not a claim
of 30 AI conversations on a $5 VPS. Use the
[presentation facts](2026-09-04-presentation-facts.md) for costs and caveats.

**What did the retrospective teach you?** Fluent generation hid incorrect keys
and formal claims. Structural checks, source-bounded review and explicit approval
must work together; revision changes must invalidate stale learner evidence.

**What is the honest current limitation?** No completed efficacy study or
measured production AI-tutoring capacity. The incomplete-answer error is fixed;
the demo publication and complete rehearsal status are tracked separately.
Passing isolated tests is not equivalent to a complete learning-loop demonstration.
