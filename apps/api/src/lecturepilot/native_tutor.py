"""Native structured tutor turns with bounded, real filesystem tools."""

import asyncio
import json
import logging
from collections import defaultdict
from contextlib import asynccontextmanager

import anyio
from pydantic_ai import Agent, ModelRetry, NativeOutput, Tool, RunContext, StructuredDict
from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, UserPromptPart
from pydantic_ai.usage import UsageLimits
from pydantic_ai.exceptions import UsageLimitExceeded, UnexpectedModelBehavior

from lecturepilot.agent_response_schema import lecturepilot_response_format
from lecturepilot.agent_tool_instructions import _with_tool_instruction, _tool_activity
from lecturepilot.agent_tool_schemas import agent_tool_schemas
from lecturepilot.authoring_provider import authoring_model
from lecturepilot.authoring_limits import authoring_budget
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.model_payload import agent_result_from_content
from lecturepilot.native_model_settings import native_model_settings, tutor_prompt_cache_key
from lecturepilot.providers import ProviderConfigurationError

TUTOR_DEADLINE_SECONDS = 120
CHAT_MAX_TOKENS = 1_500
WRITING_MAX_TOKENS = 8_192
CHAT_OUTPUT_TOKEN_LIMIT = 4_096
WRITING_OUTPUT_TOKEN_LIMIT = 16_384
logger = logging.getLogger(__name__)


def tutor_output_limits(*, writing_tools: bool) -> tuple[int, int]:
    """Return (max_tokens, output_tokens_limit).

    Turns without write/edit tools, including checkpoint assessment, stay near 1500
    output tokens. Canvas writes keep the larger per-request cap.
    """
    if writing_tools:
        return WRITING_MAX_TOKENS, WRITING_OUTPUT_TOKEN_LIMIT
    return CHAT_MAX_TOKENS, CHAT_OUTPUT_TOKEN_LIMIT


async def _native_tutor_turn(
    *,
    settings,
    turn,
    messages,
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
        else ModelRequest(parts=[UserPromptPart(m["content"])])
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
    max_tokens, output_limit = tutor_output_limits(writing_tools=bool(tools))
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
                max_tokens=max_tokens,
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
                    request_limit=7, input_tokens_limit=150_000, output_tokens_limit=output_limit
                ),
            )
            _log_cached_usage(settings.model, result.usage)
        except (UsageLimitExceeded, UnexpectedModelBehavior) as exc:
            raise ModelExecutionError(
                f"Tutor could not finish within its turn budget: {exc}"
            ) from exc
    return agent_result_from_content(json.dumps(result.output), turn, settings.model)


def _log_cached_usage(model: str, usage) -> None:
    logger.info(
        "tutor_provider_usage model=%s input_tokens=%s cached_input_tokens=%s output_tokens=%s",
        model,
        usage.input_tokens,
        usage.cache_read_tokens,
        usage.output_tokens,
    )


async def native_tutor_turn(**kwargs):
    _, output_limit = tutor_output_limits(writing_tools=kwargs.get("tool_executor") is not None)
    with authoring_budget(
        request_limit=14, input_tokens_limit=150_000, output_tokens_limit=output_limit
    ):
        try:
            async with asyncio.timeout(TUTOR_DEADLINE_SECONDS):
                return await _native_tutor_turn(**kwargs)
        except TimeoutError as exc:
            raise ModelExecutionError("Tutor turn deadline reached.") from exc
