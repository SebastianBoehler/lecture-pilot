"""Validate real tool calls against the same schemas exposed to the provider."""

from jsonschema import Draft202012Validator

from lecturepilot.agent_tool_schemas import agent_tool_schemas
from lecturepilot.agent_tool_utils import AgentToolArgumentError


_VALIDATORS = {
    tool["function"]["name"]: Draft202012Validator(tool["function"]["parameters"])
    for tool in agent_tool_schemas("evidence")
}


def validate_tool_arguments(name, args):
    validator = _VALIDATORS.get(name)
    if validator is None:
        raise AgentToolArgumentError(f"Unknown tool: {name}")
    error = next(validator.iter_errors(args), None)
    if error is not None:
        field = ".".join(str(part) for part in error.path)[:120] or "arguments"
        raise AgentToolArgumentError(f"Invalid {name} tool {field}: {error.validator} constraint.")
