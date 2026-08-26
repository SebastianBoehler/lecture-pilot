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
  --reviewer 'gemini/gemini-3.1-flash-lite=google/gemini-3.1-flash-lite@stable' \
  --reviewer 'openrouter/openai/gpt-oss-120b:nitro=openai/gpt-oss-120b@nitro' \
  --output .runtime/practice-design-benchmark.json \
  --summary
```

`--proposal-model` defaults to `LECTUREPILOT_MODEL`. `--fixtures` can select a
different frozen synthetic or clearly public corpus. Each compact
`--reviewer MODEL=CANONICAL_ID` specification separates the invocation slug
from the operator-asserted underlying model or deployment identity. Aliases or
gateways for the same deployment must use the same canonical identity; the CLI
does not infer independence from different slugs. Both identities must be
unique across at least two reviewers and both are retained in the report.
Repeated temperature-zero calls to one canonical model must not be presented
as independent evidence. The command writes the JSON report even when an
individual proposal or reviewer call fails, and returns nonzero when the
retained report contains such an error.

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
identity, both reviewer identities, production proposal, production semantic
review, per-reviewer scores and rationales, source-supported failure examples,
errors, and per-fixture summaries. `score_spread` is the maximum reviewer score
minus the minimum for that fixture and dimension; it is `null` when fewer than
two reviewers returned valid judgments. There is deliberately no opaque
readiness aggregate or automatic promotion threshold.

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
