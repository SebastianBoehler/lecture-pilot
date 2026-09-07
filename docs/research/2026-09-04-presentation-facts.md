# LecturePilot: facts to reuse in your presentation

Content only; slide design is owned by the presenter. The project is described
by the student as nine ECTS with Georg Martius, for Monday, 7 September 2026.
Administrative requirements and presentation duration are not independently verified.

## Core claim

LecturePilot separates an initial attempt, supported recovery, an independent
exit and delayed changed-form performance. It is a source-controlled learning
environment and a testable evaluation contract, not a completed efficacy study.

## Numbers you can defend

| Measure                                | Result                                                                          | What it does not mean                                                |
| -------------------------------------- | ------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| Initial main JavaScript, gzip estimate | 393.95 → 121.17 kB; **69.2% smaller**                                           | Math is deferred, not removed; not a measured loading-time gain      |
| Resource-capped authenticated reads    | **30 active clients**, 14.63 requests/s, p95 **128 ms**, zero errors over 120 s | Not 30 simultaneous AI conversations or a rented-VPS benchmark       |
| Read-test container limits             | API: 1 CPU / 512 MiB; DB: 0.5 CPU / 512 MiB                                     | Excludes OS, TLS, static web, conversion, inference and authoring    |
| Sampled peak memory in that run        | API **170.2 MiB**, Postgres **74.1 MiB**                                        | Not peak tutoring or upload memory                                   |
| No-pause burst                         | 28.8 requests/s; p95 **2.00 s**; API CPU saturated                              | This is the latency limit, not a good-UX capacity claim              |
| Explicit checkpoint assessment         | One structured completion on the successful path                                | Transport retries can add calls; ordinary chat still has a tool loop |

The test used real production-mode session authentication and Postgres, but
synthetic identities, one prepared course, warm caches and a local M4 Max Docker
host. The copied course allowed authenticated members rather than real Alma
enrollment matching. See the complete
[measurement report](2026-09-04-capacity-measurements.md) for reproducible scope.

## The “$5 VPS” answer

Current official Hetzner pricing puts a CX23 (2 shared vCPU, 4 GB RAM, 40 GB
disk) at **$7.09/month including IPv4, before VAT**, following the June 15,
2026 adjustment. This is server rent, not the full service cost. Availability
and region must be checked before purchase.
[Official prices](https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/).

The current full Compose stack has API/compiler/converter memory ceilings
totaling 6 GB before Postgres, OS and gateway. These ceilings are not measured
minimum requirements, but the full authoring stack has **not** been validated
to fit a 4 GB host. The read-only result does not change that.

The following capacity illustration reflects the September 4 configuration.
The fixed model-call ceiling was removed on September 6; these numbers are not
capacity estimates for the updated provider-budget scheduler.

For active AI learners, that same-model gate allowed three concurrent
provider requests per event loop. A planning estimate with explicit assumptions is
`headroom × 3 × seconds-between-turns / provider-slot-seconds-per-turn`.
For example, 50% headroom, one turn every 120 seconds and 10 provider-slot
seconds per turn gives 18 active learners; 30 seconds gives six. These are
**illustrations, not measured capacity**. Quotas, synchronized submissions,
retries, tokens and acceptable response time can lower the limit.

Do not quote a registered-user capacity: it depends on retained per-learner
storage, shared course sources, backup policy and usage distribution. Model
tokens, images, OCR, backups and operations are additional costs. No provider
price comparison or runtime model change was made.

## Research and retrospective

The local demo now completes all three independent practice checks. Final-code
checkpoint timings were 6.94 / 3.59 / 4.64 seconds for one three-turn episode,
using the existing Luna runtime. These are small local samples, not capacity
percentiles. See [rehearsal and latency results](2026-09-04-demo-rehearsal-results.md).

- [Learning-science brief](2026-09-04-learning-science-presentation-brief.md):
  research-to-design map and exact claim boundaries. Use
  “deliberate-practice-inspired,” not “scientifically proven tutor.”
- [Retrospective](2026-09-04-project-retrospective.md): feedback, implementation
  dates, quality failures and the shift toward revision-bound teacher control.
- [Readiness report](2026-09-04-demo-readiness.md): current tests, local demo
  changes and remaining rehearsal limitations.

Georg Martius leads Distributed Intelligence / Autonomous Learning at Tübingen,
not an autonomous-driving lab. His robotics research is a conceptual connection,
not evidence that this human-learning intervention works.
[Official group](https://uni-tuebingen.de/en/264672).

The direct local educational connection is Wagner et al. (2024): strategy
instruction and elaborated feedback in troubleshooting. It motivates actionable
feedback, but did not evaluate LecturePilot or its UI.
[Paper](https://www.sciencedirect.com/science/article/pii/S0959475223001135).
