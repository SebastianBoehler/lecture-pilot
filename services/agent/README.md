# Agent Service

This directory reserves a possible future process boundary; it is not a
deployed service today. The real provider-backed runtime lives in the FastAPI
application under `apps/api/src/lecturepilot/`.

Current runtime ownership:

- `harness.py` selects the development preview or provider-backed path;
- `model_client.py` and `agent_tool_loop.py` run LiteLLM turns and typed tools;
- workspace executors enforce logical roots and durable side effects; and
- observability records metadata-only model and tool events in production.

If the runtime is extracted later, the API and web app must continue depending
on the existing harness contract rather than a provider SDK or orchestration
framework directly.
