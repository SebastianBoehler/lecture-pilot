# API cost and semester scenarios — 6 September 2026

## Measured usage is not an account-balance statement

The approved experiment ceiling was $4. Successful provider responses reported
usage priced at **$0.668396**. Seven cancelled or otherwise uncertain calls retain
worst-case reservations totalling **$3.146438**. Conservative committed spending
is therefore **$3.814834**; the next worst-case request was blocked before sending.
Reservations are not verified invoices. The user's reported $6 balance was not
independently readable or verified, so do not infer the exact remaining balance.

The conservative reservation per unknown call is $0.4494912: the full 1.05-million
context at long-context uncached input rates plus 16,384 bounded output tokens at
the long-context output rate. Failed experiments count; they are not silently
excluded from the development budget. Reasoning tokens are already included in
output usage and are not billed twice in these calculations.

## Current model prices

Standard prices in USD per million tokens, checked against the official model
documentation during this rehearsal. Local key access listed Luna, Terra and
Astra; only Luna was used for paid tests. Codex model choice is separate.

| Model         | Input | Cached input | Output |
| ------------- | ----: | -----------: | -----: |
| GPT-5.6 Luna  |  0.20 |         0.02 |   1.20 |
| GPT-5.6 Terra |  2.00 |         0.20 |  12.00 |
| GPT-5.6 Sol   |  4.00 |         0.40 |  20.00 |
| GPT-6 Astra   | 10.00 |         1.00 |  50.00 |

Sources: [official model comparison](https://developers.openai.com/api/docs/models/compare),
[Luna](https://developers.openai.com/api/docs/models/gpt-5.6-luna),
[Astra](https://developers.openai.com/api/docs/models/gpt-6-astra).
For these long-context models, requests exceeding 272,000 input tokens use twice
the input/cache rates and 1.5 times the output rate. None of the measured samples
below crossed that threshold. Taxes, external tools, images and hosting are separate.

```txt
cost = ((input - cached) × input_rate + cached × cached_rate
        + output × output_rate) / 1,000,000
```

Astra is not the cheaper token-for-token option here. No paid Astra quality,
token-efficiency or latency comparison was conducted; retain Luna until a bounded
same-task benchmark justifies a change. A listed model is not proof of compatibility
with every runtime feature.

## What a course costs

| Measured sample                                      | Provider calls |      Cost | HTTP wall time |
| ---------------------------------------------------- | -------------: | --------: | -------------: |
| 14-lecture schedule proposal                         |              1 | $0.001682 |        7.682 s |
| Complete source-routing proposal                     |              2 | $0.000531 |        3.615 s |
| Lecture 1 evidence-ID design plus critic             |              2 | $0.009467 |       49.748 s |
| Lecture 4 successful canvas request                  |              9 | $0.019422 |       65.973 s |
| Lecture 2 successful canvas request including repair |             15 | $0.024844 |      121.400 s |
| Lecture 1 final repair only                          |             12 | $0.013453 |       68.731 s |

**There is no measured complete-course total:** all 14 designs exist, but only
three canvas drafts succeeded. Manual review/correction and failed attempts must
not be omitted from an actual operational course cost.

For a transparent planning example, assume every lecture resembles the sampled
Lecture 1 design and Lecture 2 canvas: `14 × (0.0094666 + 0.02484366) + 0.0022126`
is **$0.483 per 14-lecture course** in text-model usage. Using the Lecture 4 canvas
sample instead gives about **$0.407**. These are selected-sample extrapolations,
not an average, confidence interval or guaranteed price. Additional retries,
longer sources, re-review and optional media increase them. Fourteen lectures is
the requested scenario, not a universal university semester length.

Course generation is shared across students. At 100 students, the $0.483 scenario
amortizes to about $0.0048 per student, before ongoing tutoring and infrastructure.

## What a student costs

One real three-assessment episode used **25,286 input tokens**, including **7,750
cached**, and **1,237 output tokens**. It cost **$0.0051466** (about half a cent).
The three calls took 6.185 / 5.039 / 5.640 s without competing authoring work.
This was a scripted correctness/state-transition test, not a measured human session.

For comparison, define a session as **12 similar assessments** (four episodes),
and a semester as **two sessions per week for 14 weeks**. Reprice identical token
counts and cache hits without assuming that different models produce identical
answers, output lengths, quality or latency:

| Model | Three-call episode | 12-assessment session | 28 sessions / student |
| ----- | -----------------: | --------------------: | --------------------: |
| Luna  |           $0.00515 |              $0.02059 |                $0.576 |
| Terra |           $0.05147 |              $0.20586 |                $5.764 |
| Sol   |           $0.09798 |              $0.39194 |               $10.974 |
| Astra |           $0.24496 |              $0.97984 |               $27.436 |

Without the observed cache hits, the Luna semester scenario becomes about
**$0.733**, not $0.576. Open-ended tool-using chat, generated images, exam creation,
student uploads, retries and support costs are not represented by this narrow
assessment workload. Measure their workload mix before quoting an average student.

For 100 students under the cached Luna assumptions, tutoring is about **$57.64**
per semester. Add shared course creation and actual infrastructure separately.
An illustrative $5/month VM for six months adds $30, but this does not establish
that the complete stack fits or meets latency targets on such a VM.

## Capacity and future costs

The previous [resource-capped read measurement](2026-09-04-capacity-measurements.md)
recorded 30 active read clients at 14.63 requests/s, p95 128 ms and no errors.
It used a local Apple host, separate API/database resource caps, no live model
calls and no helper-service load. It is **not 30 concurrent AI students on a $5 VPS**.
See [the full-stack capacity note](2026-09-04-vps-capacity-sources.md) for service
limits, provider quotas and the distinction between registered and active users.

Historical illustration using the former three-call application ceiling, mean observed
assessment time 5.606 s, one assessment per active learner every 60 s, and 50%
headroom: `0.5 × 3 × 60 / 5.606 ≈ 16` active learners. At one call every 120 s,
the same arithmetic gives about 32. These are queue-utilization scenarios, **not
tested capacity**; bursts, token quotas, authoring contention and real host limits
can lower them. Registered-user count is predominantly a storage/retention question.

Do not promise a future price decline. Use sensitivity scenarios: half today's
effective token cost halves the $0.576 semester case to $0.288; twice the effective
usage doubles it to $1.153. A stronger model can win by reducing retries or tokens,
but compare measured total cost per accepted course/task, not advertised price or
a claim of greater intelligence. Recheck official pricing before presenting.
