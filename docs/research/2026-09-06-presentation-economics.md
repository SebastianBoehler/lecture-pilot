# Research presentation: learning, economics, and scale

Prepared for the research-project presentation to supervisor Georg Martius.
Sources checked 6 September 2026. Content and speaker argument, not slide design.

## The argument

Working thesis: affordable model inference makes individualized practice
economically plausible; the research challenge is making assistance lead to
independent learning. LecturePilot provides a teacher-controlled environment
in which that hypothesis can be tested.

Suggested sequence, scaled to the available presentation time:

1. **Question:** can a student solve a changed problem after support is removed?
2. **Demonstration:** attempt, targeted feedback, retry, independent check.
   Explain separately which delayed checks are planned versus demonstrated.
3. **Contribution:** professor-owned source, tasks and approval; persisted,
   revision-bound learner evidence. Show one concrete failure that motivated it.
4. **Economics:** shared course creation versus recurring learner inference.
5. **Systems evidence:** measured reader latency and course storage footprint.
6. **Prediction:** cheaper successful assistance shifts the bottleneck toward
   instructional quality, evaluation, privacy and adoption.
7. **Next experiment:** compare with a baseline, use a delayed unaided test,
   and report learning outcomes alongside costs and instructor review time.

The prediction is a hypothesis, not an established field trajectory. The strongest
ending is a falsifiable next experiment, rather than a bigger user-count claim.
Do not describe the Python/FastAPI stack as low-level implementation: its concrete
efficiencies are shared course assets and bounded model calls. Their effect needs
measurement. Source control and affordable operation alone do not prove learning.

## Historical pricing: use dated observations

USD per million standard text tokens. Historical rows are launch announcements;
the final row is a current documentation snapshot. These are different models,
not a quality-matched price index or evidence of monthly reductions.

| Date                | Model                | Input | Output | Fixed episode, no cache |
| ------------------- | -------------------- | ----: | -----: | ----------------------: |
| 25 Jan 2024         | GPT-3.5 Turbo update | $0.50 |  $1.50 |                $0.01450 |
| 18 Jul 2024         | GPT-4o mini          | $0.15 |  $0.60 |                $0.00454 |
| 14 Apr 2025         | GPT-4.1 nano         | $0.10 |  $0.40 |                $0.00302 |
| 6 Sep 2026 snapshot | GPT-5.6 Luna         | $0.20 |  $1.20 |                $0.00654 |

Sources: [January 2024 announcement](https://openai.com/index/new-embedding-models-and-api-updates/),
[4o mini launch](https://openai.com/index/gpt-4o-mini-advancing-cost-efficient-intelligence/),
[4.1 launch](https://openai.com/index/gpt-4-1/),
[current Luna documentation](https://developers.openai.com/api/docs/models/gpt-5.6-luna).

Fixed episode means the previously recorded 25,286 input and 1,237 output tokens
repriced arithmetically, without cache discounts. It is not a replay on those
models; tokenization, reasoning, retries, context support and quality differ.
January 2024 is context preceding the requested two-year window.

Do not fabricate points for one, two or four months ago from current pages.
Those require dated pricing evidence for models available then. Plot observations
as labeled points, not a smooth exponential trend. The table itself shows that
the newest inexpensive model need not have the cheapest tokens.

For a meaningful model comparison, hold the task set and acceptance rubric fixed:
report accepted-task rate, tokens including reasoning, retries, total billed cost,
and p95 latency. Cost per accepted task includes spending on rejected attempts.
Ultimately report cost per measured improvement in independent performance.

## Student and hosting scenarios

The existing [cost measurement note](2026-09-06-cost-and-latency-scenarios.md)
records one three-assessment episode at $0.0051466. A defined scenario of twelve
similar assessments per session, twice weekly for fourteen weeks gives $0.5764
per student. This is assessment inference, not a measured average student bill.
Its observed cache hits are held fixed; extra cache-write charges, if applicable
to the actual provider billing path, need reconciliation with billing records.

| Students | Scenario assessment inference / semester |
| -------: | ---------------------------------------: |
|      100 |                                   $57.64 |
|    1,000 |                                  $576.42 |
|   10,000 |                                $5,764.19 |

These are demand/budget scenarios, not supported user counts. Add:
shared authoring + VM months + backups + storage/transfer + optional media/OCR

- operations and instructor time. Do not assume these all scale proportionally.

Hetzner lists CX33 server rent at $9.99/month before IPv4 and VAT in Germany/
Finland: six months is $59.94 before those extras. This is a costing input,
not a deployment result. See the [dated price notice](https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/)
and [full-stack envelope](2026-09-04-vps-capacity-sources.md).
The current API/compiler/converter ceilings total 6 GiB, before the other services.
VM rent cannot be converted into students served until the full workload is tested.

Future sensitivity, holding quality and workload fixed:

| Effective price factor | Token-usage factor | Assessment semester scenario |
| ---------------------: | -----------------: | ---------------------------: |
|                    1.0 |                1.0 |                       $0.576 |
|                    0.5 |                1.0 |                       $0.288 |
|                    0.5 |                0.7 |                       $0.202 |
|                    1.0 |                2.0 |                       $1.153 |

These are conditional scenarios without forecast dates. Fewer tokens only help
if the same acceptance standard is maintained. More capable reasoning can also
increase tokens. Instructor review time could dominate text inference cost.

## Storage measured today

A metadata scan of the archived prepared Martius course counted 2,109 files,
307,803,127 logical bytes (307.8 MB), and 312,037,376 allocated bytes on this host.
No professor content was copied into this document.

| Component                 | Logical bytes |
| ------------------------- | ------------: |
| Sources and source assets |   304,452,122 |
| Builder records           |     2,138,177 |
| Drafts                    |       706,513 |
| Published canvas          |       505,546 |
| Analytics                 |           769 |

Ten decimal GB of dedicated course storage fits **32 copies of this snapshot**
by logical size, or **22 with 30% reserved**. Host allocated size also gives
32 and 22, respectively. This is one partial prepared-course snapshot, not a
representative distribution of complete courses. The 30% reserve is illustrative;
it does not establish a retention or backup policy.

Sources are approximately 98.9% of these bytes. Shared assets avoid copying that
source tree per student. Learner overlays, retained authoring histories, uploads,
database, logs, backups and future revisions require separate budgets.
For a 10 GB whole machine, subtract OS and container layers first. Docker image
size is not the size of the persisted course volume.

Private aggregate evidence: `output/capacity-2026-09-06/storage.json`.
The archived source path and exact measurement scope are recorded there.

## Capacity success criteria and remaining experiment

This pass repeats the existing frozen read-service image, then increases active
readers. It does not silently substitute concurrent model conversations for reads.
Use the [new benchmark report](2026-09-06-read-capacity-results.md) for actual
results and image identity.
Five existing benchmark guard tests passed before the new runs.

For a subsequent full tutoring benchmark, define a realistic turn cadence and
mix of checkpoint assessments and tool-using chat, then measure queue time,
provider time, total latency, errors, token quotas and host resources separately.
Include synchronized submissions and background authoring. Suggested provisional
criteria: under 1% errors, read p95 below 250 ms, assessment p95 below 10 seconds;
agree final product thresholds before measuring, not after seeing results.
Real inference requires its own explicit spending ceiling. A delayed provider
stub could isolate orchestration overhead but cannot establish AI capacity.
