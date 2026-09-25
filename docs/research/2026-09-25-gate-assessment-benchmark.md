# Local checkpoint assessment benchmark

Run on 25 September 2026 against the current LecturePilot checkpoint harness and ten author-written synthetic machine-learning answers in [`gate_benchmark_cases.py`](../../scripts/gate_benchmark_cases.py). Each model received the same source-backed fixture, required evidence criteria, pending independent-exit task, and structured-output contract. Calls used the configured OpenAI account and the harness's `reasoning_effort="low"`. The model allowlist was extended **only in the benchmark process**; `.env.local` and the deployed runtime model were not changed. No real learner answers or private course files were sent.

## Result

| Model | Matched expected gate status | False passes | False rejections | Provider/contract errors |
| --- | ---: | ---: | ---: | ---: |
| `openai/gpt-5.6-luna` | 10/10 | 0 | 0 | 0 |
| `openai/gpt-6-luna` | 9/10 | 0 | 1 | 0 |

The GPT-6 disagreement was `paraphrase_intro`: the answer says that parameters are fitted on labeled examples “to reduce prediction error,” then evaluated on unseen examples. The fixture expects a pass for the required criterion “Explains model optimization using a loss.” GPT-6 did not credit the `loss` criterion on that run. On three further calls of **that same item**, GPT-5.6 credited all three required criteria 3/3 times; GPT-6 did so 1/3 times and omitted `loss` 2/3 times. This is sensitivity to the wording of one borderline semantic criterion, not proof of a population-level model difference. The fixture's expected label is author-written, not independently instructor adjudicated.

An earlier attempt gave ten GPT-6 provider errors. That was a model request compatibility issue: the helper sent `temperature=0.3`, which this model rejects, and the installed LiteLLM version needs `reasoning_effort` explicitly passed through for GPT-6. [`model_request_options.py`](../../apps/api/src/lecturepilot/model_request_options.py) now sends reasoning effort without temperature and scopes the LiteLLM allowance to GPT-6. GPT-6 Chat Completions function calls require `reasoning_effort="none"`; the [tutor tool loop](../../apps/api/src/lecturepilot/agent_tool_loop.py) now selects that value for GPT-6, while retaining `low` for GPT-5. An isolated live GPT-6 function-call probe succeeded. The corrected checkpoint run above had no provider or contract errors. [OpenAI's GPT-6 Luna documentation](https://developers.openai.com/api/docs/models/gpt-6-luna) confirms the model ID and parameter boundary. A complete live LecturePilot tutor tool turn has not been exercised.

## What this benchmark does and does not test

- It exercises the **real structured checkpoint assessment path** and server-derived pass status; the [contract test](../../apps/api/tests/test_gate_benchmark_contract.py) checks the fixture is bound to a pending task, gate revision and publication version.
- It tests gate **status** on ten English examples spanning strong, incomplete, paraphrased, contradictory and uncertain answers. It does not score all evidence IDs, other subjects, German answers, genuine student writing, or response consistency beyond the one repeated case.
- It does **not** test whether feedback is useful. The fixtures have no approved hint ladder, and the server composes feedback from missing criteria. Feedback quality needs an instructor-rated sample: error diagnosis, actionable next step, whether the support fits the misconception, and answer leakage into the fresh task.
- It does **not** measure learning. Neither a high match rate nor human agreement would establish improved delayed unaided transfer.

## Next calibration set

Use approved LecturePilot tasks from several subjects and languages. Have at least two qualified human raters independently label the exact required evidence IDs in a pilot set of roughly 60–100 *de-identified or consented* answers, then adjudicate disagreements before comparing models. Include correct paraphrases, missing steps, wrong-direction reasoning, confident misconceptions, partial calculations, empty/uncertain replies and attempts after help. Report false-pass and false-rejection rates, criterion-level agreement, model variability on repeated items, and disagreement examples by subject/language. Evaluate feedback separately with a rubric and then test a learner-facing change on delayed independent changed tasks. The initial 60–100 item set is for error discovery and protocol refinement, not a precise rare-error estimate.

## Verification

- `pytest -q apps/api/tests/test_model_request_reliability.py apps/api/tests/test_gate_benchmark_contract.py apps/api/tests/test_checkpoint_model_request.py`: **19 passed**, including a mocked GPT-6 tutor tool request.
- `ruff check` on the changed source and test files: **passed**.
- The benchmark script completed after the compatibility fix: **10 GPT-5.6 calls and 10 GPT-6 calls**, plus three repeat calls per model for the disputed item.

Reproduce the ten-case comparison with `LECTUREPILOT_ALLOWED_MODELS=openai/gpt-5.6-luna,openai/gpt-6-luna .venv/bin/python scripts/benchmark_gate_models.py --model openai/gpt-5.6-luna --model openai/gpt-6-luna`. This requires a configured local OpenAI API key and makes paid provider calls. The script prints status comparisons; the three-item repeat check was a separate one-off call of the same `paraphrase_intro` fixture.

## Jev as a candidate criterion judge

TypeSafe's [Jev API](https://docs.typesafe.ai/introduction) accepts one state plus several typed questions and returns probabilities rather than prose. That fits our approved atomic evidence criteria: submit one yes/no (Noul) question per required criterion, with the exact task, student answer, source excerpt and rubric in the state; let LecturePilot's existing server logic combine criterion results into pass/missing evidence and select approved support. Jev would **judge evidence**, not write feedback or choose a new task. Its probability would require a threshold calibrated against adjudicated human labels; a typed answer can still be wrong.

Two new, currently preprint studies support testing rather than immediate replacement. [Rao and Callison-Burch](https://arxiv.org/abs/2609.29769) find Jev competitive on many binary rubric criteria and cheaper/faster than their LLM comparators, but weaker on some graded criteria; fallback judges often repeat Jev's confident errors. [Li et al.](https://arxiv.org/abs/2609.26550) find a confidence-based escalation can retain much of a stronger judge's accuracy on their tasks, while derivation checking and polished but wrong answers remain hard. Neither paper tests LecturePilot's university-course gates. We should measure **false passes first**, then false rejections, criterion-level agreement, calibration, repeated-call stability, latency, cost and error overlap with GPT-5.6/GPT-6 Luna on the same instructor-adjudicated cases. Shadow evaluation should leave learner outcomes unchanged until that comparison is credible.

No `JEV`/`TYPESAFE` API credential or integration is configured in this checkout, so no live Jev scores are reported here. The current ten synthetic cases are too small to select a judge or tune a confidence threshold without overfitting.
