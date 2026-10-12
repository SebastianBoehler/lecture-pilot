"""Native structured tutor turns with bounded, real filesystem tools."""

import asyncio
import json
import logging
from collections import defaultdict
from contextlib import asynccontextmanager

import anyio
from pydantic_ai import Agent, ModelRetry, NativeOutput, Tool, RunContext, StructuredDict
from pydantic_ai.messages import CachePoint, ModelRequest, ModelResponse, TextPart, UserPromptPart
from pydantic_ai.usage import UsageLimits
from pydantic_ai.exceptions import UsageLimitExceeded, UnexpectedModelBehavior

from lecturepilot.agent_response_schema import lecturepilot_response_format
from lecturepilot.agent_tool_instructions import _with_tool_instruction, _tool_activity
from lecturepilot.agent_tool_schemas import agent_tool_schemas
from lecturepilot.authoring_provider import authoring_model
from lecturepilot.authoring_limits import authoring_budget
from lecturepilot.metadata_events import emit_metadata_event
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.model_payload import agent_result_from_content
from lecturepilot.native_model_settings import native_model_settings, tutor_prompt_cache_key
from lecturepilot.providers import ProviderConfigurationError
from lecturepilot.tutor_turn_budget import (
    TUTOR_INPUT_TOKEN_LIMIT,
    TUTOR_REQUEST_LIMIT,
    TutorTurnBudget,
    tutor_turn_budget,
)

TUTOR_DEADLINE_SECONDS = 120
logger = logging.getLogger(__name__)


def _user_part(message: dict) -> UserPromptPart:
    # The marker ends the prefix shared by all learners of one lecture publication.
    if message.get("cache_boundary"):
        return UserPromptPart([message["content"], CachePoint()])
    return UserPromptPart(message["content"])


async def _native_tutor_turn(
    *,
    settings,
    turn,
    messages,
    budget: TutorTurnBudget,
    usage_recorder=None,
    model=None,
    tool_executor=None,
    tool_profile="tutor",
    observability=None,
    emit=None,
):
    # System rules and stable lecture context precede the sliding conversation.
    messages = (
        _with_tool_instruction(messages, tool_profile) if tool_executor is not None else messages
    )
    instructions = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
    conversation = [m for m in messages if m["role"] != "system"]
    history = [
        ModelResponse(parts=[TextPart(m["content"])])
        if m["role"] == "assistant"
        else ModelRequest(parts=[_user_part(m)])
        for m in conversation[:-1]
    ]
    prompt = conversation[-1]["content"]
    calls_per_step = defaultdict(int)
    tool_count = 0

    def create_tool(definition):
        name = definition["name"]

        async def execute(ctx: RunContext, **args):
            nonlocal tool_count
            calls_per_step[ctx.run_step] += 1
            tool_count += 1
            if calls_per_step[ctx.run_step] > 6 or tool_count > 36:
                return {
                    "ok": False,
                    "error": "Tutor tool-call budget exhausted. Finish the current turn.",
                }
            if emit:
                emit(_tool_activity(name, args))
            if observability is None:
                return await anyio.to_thread.run_sync(tool_executor.execute, name, args)
            with observability.tool_span(f"agent_tool_{name}", tool=name) as span:
                result = await anyio.to_thread.run_sync(tool_executor.execute, name, args)
                span.set_outputs({"ok": result.get("ok"), "error": result.get("error")})
                return result

        return Tool.from_schema(
            execute,
            name=name,
            description=definition.get("description"),
            json_schema=definition["parameters"],
            takes_ctx=True,
            sequential=True,
        )

    tools = (
        [create_tool(schema["function"]) for schema in agent_tool_schemas(tool_profile)]
        if tool_executor is not None
        else []
    )
    publication_version = (
        turn.analytics_context.publication_version if turn.analytics_context else None
    )

    @asynccontextmanager
    async def provider():
        if model is not None:
            yield model
        else:
            async with authoring_model(
                settings, usage_recorder, lambda: None, stage="tutor_turn"
            ) as gateway:
                yield gateway

    async with provider() as gateway:
        agent = Agent(
            gateway,
            instructions=instructions,
            tools=tools,
            output_type=NativeOutput(
                StructuredDict(lecturepilot_response_format(turn)["json_schema"]["schema"]),
                strict=True,
            ),
            retries=2,
            model_settings=native_model_settings(
                settings,
                temperature=0.3,
                max_tokens=budget.max_tokens,
                tool_calls=bool(tools),
                prompt_cache_key=tutor_prompt_cache_key(
                    settings,
                    course_id=turn.course_id,
                    lecture_id=turn.lecture_id,
                    publication_version=publication_version,
                ),
            ),
        )

        @agent.output_validator
        def validate(ctx, output):
            if tool_executor is not None:
                pending = tool_executor.pending_canvas_edit_instruction()
                if pending:
                    raise ModelRetry(pending)
            try:
                agent_result_from_content(json.dumps(output), turn, settings.model)
            except ProviderConfigurationError as exc:
                raise ModelRetry(str(exc)) from exc
            return output

        try:
            result = await agent.run(
                prompt,
                message_history=history,
                usage_limits=UsageLimits(
                    request_limit=TUTOR_REQUEST_LIMIT,
                    input_tokens_limit=TUTOR_INPUT_TOKEN_LIMIT,
                    output_tokens_limit=budget.output_tokens_limit,
                ),
            )
            _record_turn_usage(settings.model, budget, result.usage)
        except (UsageLimitExceeded, UnexpectedModelBehavior) as exc:
            raise ModelExecutionError(
                f"Tutor could not finish within its turn budget: {exc}"
            ) from exc
    return agent_result_from_content(json.dumps(result.output), turn, settings.model)


def _record_turn_usage(model: str, budget: TutorTurnBudget, usage) -> None:
    """One event per turn so prefix-cache hit rate can be measured per turn kind."""
    emit_metadata_event(
        "tutor.turn_usage",
        model=model,
        stage=budget.kind,
        requested_count=usage.requests,
        input_tokens=usage.input_tokens,
        cached_input_tokens=usage.cache_read_tokens,
        output_tokens=usage.output_tokens,
    )


async def native_tutor_turn(**kwargs):
    budget = tutor_turn_budget(kwargs["turn"], tools=kwargs.get("tool_executor") is not None)
    # Provider-level transport retries may add requests beyond the agent's own request limit.
    with authoring_budget(
        request_limit=TUTOR_REQUEST_LIMIT * 2,
        input_tokens_limit=TUTOR_INPUT_TOKEN_LIMIT,
        output_tokens_limit=budget.output_tokens_limit,
    ):
        try:
            async with asyncio.timeout(TUTOR_DEADLINE_SECONDS):
                return await _native_tutor_turn(budget=budget, **kwargs)
        except TimeoutError as exc:
            raise ModelExecutionError("Tutor turn deadline reached.") from exc
