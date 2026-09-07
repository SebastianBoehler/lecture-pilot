# LecturePilot presentation outline

Working structure, 7 September 2026. The presenter creates the slides.
Visual direction: black background, white type, one central idea per slide,
usually one screenshot/diagram or two to three brief points. Keep numerical
qualifications in a readable footnote and explanations in speaker notes.
Confirmed duration: 15–20 minutes. Use fifteen slides and rehearse for about
18 minutes, including a three-minute demonstration. The slide allocations total
17 minutes, with approximately one minute for transitions and additional margin
within the 20-minute maximum.

## Narrative

I started by generating learning materials. During this project, the question
became how to design assistance that helps students become independently capable.
That changed the system: professor-defined goals, adaptable teaching, explicit
learning evidence, and a practical path toward affordable university use.

## Slide 2: outline shown to the audience

1. From quiz generation to a learning problem
2. How research shaped the design
3. How LecturePilot works
4. What early testing shows
5. Where I want to take it next

These five headings organize the talk. They do not require separate divider
slides. The slide titles below can carry the transitions.

## The dependency between ideas

Use this chain to decide whether a slide belongs and where it goes:

Earlier prototype → unresolved learning problem → relevant research → changed
requirements → professor-defined goals → learner experience → supporting
architecture → observed usage → cost and scale → unanswered questions → next steps.

Each transition answers a question raised by the preceding slide:

- Prototype to problem: “It generated quizzes. What would make it a tutor?”
- Problem to research: “What would count as learning, and what might support it?”
- Research to design: “What did that change about what I built?”
- Goals to demonstration: “What does this mean for a student using the tool?”
- Demonstration to architecture: “What needs to happen behind that interaction?”
- Architecture to usage: “What happened when people actually tried it?”
- Usage to economics: “Could this be practical beyond that small testing phase?”
- Results to next steps: “What is promising, what is still unproven, and what will I do next?”

The personal ending follows from the work: the project deepened the presenter's
interest in educational research, opened the Hector Institute connection, and
motivates continued development and professor onboarding. It should feel like
where this investigation led, rather than an unrelated career announcement.

Do not open with architecture, token prices or a feature inventory: the audience
first needs the learning problem that makes those details relevant. Define only
the concepts required for the next step; this is a research-project narrative,
not a separate introductory lecture on AI or neuroscience.

## Slide-by-slide authoring guide

| Slide | Suggested title                       | Main point and visual                                                                                               | Time |
| ----: | ------------------------------------- | ------------------------------------------------------------------------------------------------------------------- | ---: |
|     1 | Existing title slide                  | Keep the chosen title; introduce yourself                                                                           | 0:15 |
|     2 | Outline                               | Five section headings below                                                                                         | 0:15 |
|     3 | Where I started                       | Study Assistant screenshot from March 2025; upload documents and generate exams                                     | 1:00 |
|     4 | What should an AI tutor optimize?     | Assisted success versus later independent capability                                                                | 1:00 |
|     5 | What supports learning?               | Objectives first; retrieval and application; feedback and fading                                                    | 1:30 |
|     6 | Research connections in Tübingen      | Wagner: feedback formulation; Himmer: rehearsal and sleep. Explain implications without claiming product validation | 1:00 |
|     7 | How the project evolved               | Generated content → source-grounded practice → approved goals and independent evidence                              | 1:00 |
|     8 | The professor defines the goal        | Sources → approved goals → AI teaching and repair → professor publication                                           | 1:00 |
|     9 | A learner's path through LecturePilot | Three-minute rehearsed workflow: attempt, help, fresh independent task. Include language only if rehearsed          | 3:00 |
|    10 | How the system is organized           | One diagram of shared services, isolated helpers, external inference and personal storage                           | 1:00 |
|    11 | Early production testing              | 40 accounts · 20 tutor-active · 309 requests; median 9.5 beneath                                                    | 1:00 |
|    12 | What does the inference cost?         | Measured assessment episode, explicit semester scenario, one conditional future-cost statement                      | 1:30 |
|    13 | What can a small deployment support?  | 30 active readers: p95 138 ms; personal text: 38.3 → 7.4 KB. Keep units and scope visible                           | 1:00 |
|    14 | What comes next?                      | Test independent learning; make professor onboarding intuitive; continue supporting introductions                   | 1:30 |
|    15 | Where this project takes me next      | Hector Institute connection and continued development; close on the research purpose                                | 1:00 |

## Narrative transitions and speaker emphasis

### Starting point: slides 3–4

The earlier prototype establishes the baseline, rather than serving as a second
product demonstration. Explain what it could do and what it could not establish.
The matching repository is `study-assistant`; its README screenshot was added
on 30 March 2025. Use the unchanged copy in `output/presentation-assets/`.

Transition: “Generating questions was possible. The research challenge was
deciding what the student should learn and whether the interaction helped.”

### Research and evolution: slides 5–8

Avoid a literature inventory. For each principle, connect the finding to one
implementation decision. Worked guidance depends on prior knowledge; difficulty
alone is not beneficial. Neuroscience motivates memory questions and does not
certify the effectiveness of the application.

The Tübingen slide can distinguish educational experiments on feedback from
neuroscience experiments on memory. Martius's autonomous-learning research is
a conceptual connection; do not attribute other groups' studies to his lab.

Slide 7 should show two or three actual changes, not every feature or commit:

- Too little meaningful practice → checks placed at useful transitions.
- Fluent but wrong generated material → source-grounded semantic review.
- Overly rigid or confused ownership → approved intent separated from repairable teaching.

Use the current ownership model on slide 8: professors approve goals, constraints
and explicitly fixed tasks. AI can repair its unpublished teaching implementation
without changing approved intent. Professors still review and publish the final
canvas. Do not reuse the older claim that every generated task is immutable as
soon as a learning goal is approved.

### Product: slides 9–10

Use one concept throughout. Show its goal, one explanation, one learner attempt
and the resulting support. A screenshot sequence is easier to control than a long
live session. Rehearse the exact build and distinguish scripted demonstration
from observed human learning.

Current repo instructions describe German/English published explanation variants,
preserving canonical assessments. Reverify the UI before demonstrating; the
earlier September 6 note predates this addition. French remains a proposed
extension unless verified. Do not promise that every objective is language-neutral.

Restyle the existing architecture diagram to match the black/white deck.
Emphasize responsibilities and shared storage. Put container limits, startup
jobs and detailed networking in backup material if the diagram becomes crowded.

### Numbers: slides 11–13

Slide 11: production was inspected on September 6, but recorded tutor activity
was July 23–August 5, mostly July 23–24. Accounts are not verified unique people;
309 counts admitted requests, not confirmed completions. These are early-version
usage figures, not validation of the newest learning workflow.

Slide 12: a prior scripted episode cost $0.0051466. Twelve similar assessments
per session, twice weekly for fourteen weeks extrapolates to about $0.58 per
student for assessment inference. This excludes open chat, images, exams,
retries, infrastructure and instructor labor. It is not a typical student bill.
Shared course preparation was estimated at $0.41–$0.48 from selected successful
samples; no complete-course total was measured. Keep that estimate in backup
if it distracts from the stronger episode measurement.

Pricing backup slide: use actual dated model price observations; do not manufacture monthly
price points or draw a guaranteed exponential decline. Model capabilities and
token usage differ. Show future cost factors as scenarios, not dates or forecasts.
Include the possibility that lower price is offset by greater reasoning usage.

Slide 13: label readers, disk storage and compressed archives separately. The
read test used the frozen September 4 image on a local M4 Max Docker host, with
one CPU/512 MiB API and half CPU/512 MiB DB. It excludes live inference and
helper-service load. At 60 readers p95 rose to 1.92 seconds; show this in backup.
The compression demonstration used one sparse learner sample and is not active
storage compression. A 10 GB capacity calculation needs an explicit per-learner
budget and excludes shared course files, database and operating system.

### Closing: slides 14–15

Frame the next study around delayed unaided performance against a meaningful
comparison, then measure instructor effort and cost. Avoid treating completion,
engagement or model correctness as interchangeable with learning.

For adoption: “I am happy to introduce the tool to professors. My design goal is
that creating a first course should not require me to be in the room.”
An independent professor onboarding test is a concrete way to evaluate that goal.

The user reports that this project and growing education-research interest led
to a research-assistant connection at the Hector Institute. State the exact
employment stage in the presenter's own words; do not imply institutional
endorsement, funding or collaboration on LecturePilot without evidence.

Suggested final sentence: “I want to continue building a tool that professors
can use independently, and test whether it helps students do the same.”

## Backup material

- Full provider price table, token accounting and hosting arithmetic.
- Read benchmark workload, resource limits and 30/60-reader comparison.
- 10 GB storage scenarios: 1 MB/student → 7,000; 10 MB → 700; 100 MB → 70,
  after 30% reserve in a dedicated learner-data volume. These are assumptions.
- Research citations and the contrasting controlled AI-tutoring results.
- Full production usage definitions and limitations.

For a strict 15-minute slot, shorten the demo to two minutes and move slide 13
into backup. For a 20-minute slot, add a one-minute historical-pricing slide
before the future outlook, or use the time for a clearer demonstration. Do not
add both unless rehearsal leaves sufficient margin.

## Evidence and assets

- [Project retrospective](2026-09-04-project-retrospective.md)
- [Research, objectives and language](2026-09-06-objectives-language-and-learning.md)
- [Current intent ownership](../learning-intent-ownership.md)
- [Current learning evidence and teaching languages](../learning-evidence-flow.md)
- [Production usage](2026-09-06-production-testing-usage.md)
- [Cost and latency samples](2026-09-06-cost-and-latency-scenarios.md)
- [Pricing and economic scenarios](2026-09-06-presentation-economics.md)
- [Read benchmark](2026-09-06-read-capacity-results.md)
- [Learner storage](2026-09-06-learner-storage-and-compression.md)

Screenshot identified: Study Assistant, 2025. Still to rehearse: selected
current learner workflow, professor-goal screen, German/English example, final
demo timing. No slides or application code were changed in this pass.

Detailed copy and citations: [research-slide content](2026-09-07-research-slide-content.md).
