# Practice-design pedagogical quality benchmark

This opt-in benchmark sends each committed synthetic source packet through the
real production practice-design planner, validates the result as a
`PracticeDesignProposal`, retains the production `PracticeDesignReviewResult`,
and asks at least two distinct configured models for separate structured
judgments. It contains no professor material or learner workspace data and is
not a CI quality gate.

## Run it

Install the API `agent` extra and configure provider keys plus
`LECTUREPILOT_ALLOWED_MODELS` for the proposal model and every reviewer model.
Then run:

```bash
python scripts/benchmark_practice_design.py \
  --proposal-model openai/gpt-5.6-luna \
  --reviewer 'gemini/gemini-3.1-flash-lite=google/gemini-3.1-flash-lite@stable|google-api/eu' \
  --reviewer 'openrouter/openai/gpt-oss-120b:nitro=openai/gpt-oss-120b@2026-07|openrouter/nitro' \
  --output .runtime/practice-design-benchmark.json \
  --summary
```

`--proposal-model` defaults to `LECTUREPILOT_MODEL`. `--fixtures` can select a
different frozen synthetic or clearly public corpus. Each compact
`--reviewer MODEL=UNDERLYING_ID[|DEPLOYMENT]` specification separates the
invocation slug from the required canonical underlying model/version or
materially distinct fine-tune identity. The optional deployment value records
gateway, endpoint, region, or deployment provenance for audit only. Two
gateways or deployments serving the same underlying weights must use the same
underlying identity and are rejected as separate reviewers. Invocation slugs
must also be unique as a configuration-consistency guard, so one configured
target cannot be relabeled with conflicting claimed identities. Distinct
invocation slugs are necessary but insufficient evidence of independence.
Deployment provenance never establishes independence; only distinct underlying
identities qualify for reviewer disagreement. Repeated temperature-zero calls
to one underlying model must not be presented as independent evidence. The
command writes the JSON report even when an individual proposal or reviewer
call fails, and returns nonzero when the retained report contains such an
error.

## Dimensions and scale

Every reviewer scores all dimensions separately:

- source faithfulness
- measurable outcomes
- task answerability
- exit equivalence
- transfer invariant and novelty
- rubric sufficiency
- hint leakage
- misconception plausibility
- source coverage

The bounded scale is retained in every report:

- **1 — Unusable:** contradicted, unsupported, leaked, or not assessable.
- **2 — Major defects:** substantial repair is needed before use.
- **3 — Mixed:** usable elements remain, but a material weakness persists.
- **4 — Sound:** no major defect, with a minor specific limitation.
- **5 — Strong:** fully satisfies the dimension with no material defect found.

Each submaximal score requires a textual rationale and a failure example backed
by an exact routed source excerpt. A target-specific example uses
`scope: "target"` and at least one exact target ID; a proposal-wide example uses
`scope: "global"` and no target IDs. Reports preserve the configured proposal
model, production proposal, production semantic review, per-reviewer scores and
rationales, source-supported failure examples, errors, and per-fixture
summaries. Each reviewer record retains the invocation slug, underlying model
identity, and optional deployment provenance.
`score_spread` is the maximum reviewer score minus the minimum for that fixture
and dimension; it is `null` when fewer than two reviewers returned valid
judgments. There is deliberately no opaque readiness aggregate or automatic
promotion threshold.

## What this can and cannot establish

The benchmark audits whether a provider proposal satisfies the supplied source
and pedagogical contract across a small multi-discipline fixture set. It can
inform prompt/model selection and reveal reviewer disagreement. Synthetic
fixtures and model judgments cannot establish that learners learned, retained,
or transferred the capability.

Only a prospective learner evaluation measuring unaided independent exits and
delayed changed-form transfer can support a learning-effect claim. Assisted
correctness, engagement, confidence, professor approval, and this benchmark do
not support that claim.
