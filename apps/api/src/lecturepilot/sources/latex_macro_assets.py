from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class AssetMacro:
    name: str
    argument_count: int
    optional_default: str | None
    path_templates: tuple[str, ...]


def expanded_macro_asset_references(sources: list[str]) -> list[str]:
    macros: dict[str, AssetMacro] = {}
    for source in sources:
        for macro in _read_asset_macros(source):
            macros[macro.name] = macro
    references: list[str] = []
    for source in sources:
        for macro in macros.values():
            references.extend(_expand_invocations(source, macro))
    return list(dict.fromkeys(references))


def _read_asset_macros(source: str) -> list[AssetMacro]:
    macros = []
    for match in _NEW_COMMAND_RE.finditer(source):
        position = _skip_space(source, match.end())
        argument_count = 0
        optional_default = None
        if position < len(source) and source[position] == "[":
            raw_count, position = _group(source, position, "[", "]")
            if raw_count is None or not raw_count.strip().isdigit():
                continue
            argument_count = int(raw_count.strip())
            position = _skip_space(source, position)
        if position < len(source) and source[position] == "[":
            optional_default, position = _group(source, position, "[", "]")
            if optional_default is None:
                continue
            position = _skip_space(source, position)
        body, _ = _group(source, position, "{", "}")
        if body is None:
            continue
        templates = tuple(
            path
            for path in (item.group("path").strip() for item in _ASSET_RE.finditer(body))
            if "#" in path
        )
        if templates and argument_count <= 9:
            macros.append(
                AssetMacro(
                    name=match.group("name"),
                    argument_count=argument_count,
                    optional_default=optional_default,
                    path_templates=templates,
                )
            )
    return macros


def _expand_invocations(source: str, macro: AssetMacro) -> list[str]:
    references = []
    invocation = re.compile(rf"\\{re.escape(macro.name)}(?![A-Za-z@])")
    for match in invocation.finditer(source):
        position = _skip_space(source, match.end())
        arguments: list[str] = []
        if macro.optional_default is not None:
            optional = macro.optional_default
            if position < len(source) and source[position] == "[":
                optional, position = _group(source, position, "[", "]")
                if optional is None:
                    continue
                position = _skip_space(source, position)
            arguments.append(optional)
        required = macro.argument_count - len(arguments)
        for _ in range(required):
            argument, position = _group(source, position, "{", "}")
            if argument is None:
                break
            arguments.append(argument)
            position = _skip_space(source, position)
        if len(arguments) != macro.argument_count:
            continue
        for template in macro.path_templates:
            expanded = template
            for index, argument in enumerate(arguments, start=1):
                expanded = expanded.replace(f"#{index}", argument.strip())
            references.append(expanded)
    return references


def _group(source: str, position: int, opening: str, closing: str) -> tuple[str | None, int]:
    if position >= len(source) or source[position] != opening:
        return None, position
    depth = 0
    for index in range(position, len(source)):
        character = source[index]
        if character == opening and (index == 0 or source[index - 1] != "\\"):
            depth += 1
        elif character == closing and (index == 0 or source[index - 1] != "\\"):
            depth -= 1
            if depth == 0:
                return source[position + 1 : index], index + 1
    return None, position


def _skip_space(source: str, position: int) -> int:
    while position < len(source) and source[position].isspace():
        position += 1
    return position


_NEW_COMMAND_RE = re.compile(r"\\(?:re)?newcommand\s*\{\\(?P<name>[A-Za-z@]+)\}")
_ASSET_RE = re.compile(
    r"\\(?:includegraphics|ig|igh)(?:<[^>]*>)?(?:\[[^]]*])?\s*\{(?P<path>[^{}]+)}"
)
