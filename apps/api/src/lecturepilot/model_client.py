from __future__ import annotations

import json
from collections.abc import Callable
from typing import Protocol

from lecturepilot.agent_tool_executor import AgentToolExecutor
from lecturepilot.agent_tool_loop import complete_tool_turn
from lecturepilot.agent_tool_schemas import AgentToolProfile, tutor_tool_profile_for_message
from lecturepilot.agent_response_schema import lecturepilot_response_format
from lecturepilot.learning_gates import gate_rubric_context
from lecturepilot.model_commands import canvas_context
from lecturepilot.model_payload import agent_result_from_content
from lecturepilot.models import (
    AgentTurnInput,
    AgentTurnResult,
    ProviderSettings,
)
from lecturepilot.observability import Observability
from lecturepilot.providers import ProviderConfigurationError


class ModelExecutionError(RuntimeError):
    """Raised when the configured model provider rejects or fails a request."""


class ModelClient(Protocol):
    async def complete_turn(
        self,
        *,
        settings: ProviderSettings,
        turn: AgentTurnInput,
        tool_executor: AgentToolExecutor | None = None,
        observability: Observability | None = None,
        emit: Callable[[str], None] | None = None,
        tool_profile: AgentToolProfile | None = None,
    ) -> AgentTurnResult:
        """Complete one tutor turn."""


class LiteLLMModelClient:
    async def complete_turn(
        self,
        *,
        settings: ProviderSettings,
        turn: AgentTurnInput,
        tool_executor: AgentToolExecutor | None = None,
        observability: Observability | None = None,
        emit: Callable[[str], None] | None = None,
        tool_profile: AgentToolProfile | None = None,
    ) -> AgentTurnResult:
        try:
            from litellm import acompletion
        except ImportError as exc:
            raise ProviderConfigurationError(
                'litellm is not installed. Install the backend with the "agent" extra.'
            ) from exc

        try:
            if tool_executor is not None:
                return await complete_tool_turn(
                    acompletion=acompletion,
                    settings=settings,
                    turn=turn,
                    tool_executor=tool_executor,
                    observability=observability or Observability(),
                    emit=emit,
                    messages=_messages(turn),
                    tool_profile=tool_profile or tutor_tool_profile_for_message(turn.message),
                )
            response = await acompletion(
                model=settings.model,
                messages=_messages(turn),
                temperature=0.3,
                response_format=lecturepilot_response_format(),
            )
        except ProviderConfigurationError:
            raise
        except Exception as exc:
            raise ModelExecutionError(
                "Model request failed. Check the provider key and model configuration."
            ) from exc
        return agent_result_from_content(response.choices[0].message.content, turn, settings.model)


def _messages(turn: AgentTurnInput) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You are LecturePilot, a text-first university tutor. "
                "Lead the tutoring flow from the current lecture canvas. "
                "Do not ask open-ended preference questions such as what the student wants. "
                "Use one concrete next check or instruction per turn. "
                "Attendance selects the tutor stance: present means verification mode, "
                "absent means guided walkthrough mode, unknown means diagnostic mode. "
                "In verification mode, behave like an examiner and coach: check whether the "
                "student understood each key learning goal, give feedback on what is secure "
                "or missing, and use quizzes only after orienting them to the relevant canvas claim. "
                "In guided walkthrough mode, behave like a teacher for an absent student: "
                "walk through the section reasoning, examples, and formulas in small steps, "
                "avoid overwhelming summaries, and only move to quality gates after teaching "
                "the material needed for that gate. "
                "Still respond to the student's concrete request and the current canvas section. "
                "Decide whether the active quality gate passed, needs_evidence, or was not_assessed. "
                "Do not mark a gate passed from keywords or a definition-only answer. "
                "A gate can pass only with evidence across definition, mechanism, computation, "
                "and transfer or failure mode. "
                "Use the active quality-gate rubric as the complete pass contract; do not "
                "invent additional required concepts once the listed evidence groups are covered. "
                "If evidence is partial, return needs_evidence and ask one concrete missing "
                "worked-example check. "
                "Return one structured tutor response with message, canvas_commands, and quality_gate. "
                "canvas_commands must contain focus_section and highlight_span commands. "
                "Canvas editing is a real tool call: when the student asks to append, add, "
                "create, generate, update, edit, or extend a canvas section, note, example, "
                "infographic, diagram, table, chart, graph, plot, or visual, include exactly "
                "one append_section or update_section command with a student-facing "
                "CanvasSection using paragraph, callout, list, math, table, checkpoint, "
                "quiz, or component blocks. Quiz blocks use text as the question and "
                "items as answers. Component blocks are real file-backed interactive "
                "artifacts: use type component, component_id, component_type, "
                "component_version, text as the prompt, options with id/text/correct, "
                "or option_ids plus answer_index. "
                "Checkpoint blocks use text as the evidence the student must produce. "
                "If the student asks for an infographic, diagram, image, visual, plot, "
                "chart, graph, or table, still return the section command; the harness will "
                "materialize the raster image asset and attach it to the section. "
                "Never say you added, appended, generated, inserted, or updated canvas "
                "content unless canvas_commands contains that append_section or "
                "update_section command. "
                "Use focus_section to scroll to the section that supports your next check, "
                "not just the current section. "
                "Use highlight_span with a block id and short phrase when a precise sentence, "
                "list, formula, or asset supports the explanation. "
                "Only use section_id and span_id values from the canvas context; do not "
                "return multiple focus_section commands. "
                "quality_gate must be an object with gate_id, status, reason, and next_prompt. "
                "Use bayes-decision-check for lecture-03. For other lectures use "
                "lecture-learning-outcome-check."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Lecture id: {turn.lecture_id}\n"
                f"Attendance: {turn.attendance.value}\n"
                "Current section: "
                f"{turn.canvas_state.focused_section_id or 'bayesian-decision-theory-the-aim'}\n"
                f"{_user_memory_context(turn)}\n"
                f"{_readiness_scaffold_context(turn)}\n"
                f"{gate_rubric_context(turn.lecture_id)}\n"
                f"{canvas_context(turn)}\n"
                f"Student message: {turn.message}"
            ),
        },
    ]


def _user_memory_context(turn: AgentTurnInput) -> str:
    preferences = json.dumps(turn.user_memory.preferences, ensure_ascii=True, sort_keys=True)
    global_notes = turn.user_memory.global_notes.strip() or "none"
    course_notes = turn.user_memory.course_notes.strip() or "none"
    return (
        "Durable user memory:\n"
        f"- preferences: {preferences}\n"
        f"- global notes: {global_notes}\n"
        f"- course notes: {course_notes}\n"
        "Use this only to adapt examples, pace, and explanation style. "
        "Do not treat memory as course evidence."
    )


def _readiness_scaffold_context(turn: AgentTurnInput) -> str:
    task = turn.readiness_task
    if task is None:
        return "Active readiness scaffold policy: none."
    policy = task.scaffold_policy
    if policy is None:
        return "Active readiness scaffold policy: none."
    return (
        "Active readiness scaffold policy:\n"
        f"- task_id: {task.id}\n"
        f"- trigger: {policy.trigger}\n"
        f"- learner_stage: {policy.learner_stage}\n"
        f"- profile: {policy.profile}\n"
        f"- process_label: {policy.process_label}\n"
        f"- source_ref: {task.source_ref or 'canvas section'}\n"
        f"- expected_evidence: {task.expected_evidence}\n"
        f"- tutor_move: {policy.tutor_move}\n"
        f"- forbidden: {policy.forbidden}"
    )
