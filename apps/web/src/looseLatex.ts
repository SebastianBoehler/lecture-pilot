type MarkdownNode = {
  type?: string;
  value?: string;
  data?: Record<string, unknown>;
  children?: MarkdownNode[];
};

type MathRange = { start: number; end: number };

export function looseLatexPlugin() {
  return (tree: unknown) => {
    splitLooseLatexText(tree as MarkdownNode);
    return tree;
  };
}

function splitLooseLatexText(node: MarkdownNode) {
  if (!node || blockedMarkdownNode(node) || !Array.isArray(node.children)) return;
  const next = [];
  for (const child of node.children) {
    if (child.type === "text" && typeof child.value === "string") {
      next.push(...looseLatexPieces(child.value));
    } else {
      splitLooseLatexText(child);
      next.push(child);
    }
  }
  node.children = next;
}

function looseLatexPieces(value: string): MarkdownNode[] {
  const ranges = looseMathRanges(value);
  if (!ranges.length) return [textNode(value)];
  const pieces: MarkdownNode[] = [];
  let cursor = 0;
  for (const range of ranges) {
    if (range.start > cursor) pieces.push(textNode(value.slice(cursor, range.start)));
    pieces.push(inlineMathNode(normalizeLooseLatex(value.slice(range.start, range.end))));
    cursor = range.end;
  }
  if (cursor < value.length) pieces.push(textNode(value.slice(cursor)));
  return pieces;
}

function looseMathRanges(value: string) {
  const commandRanges = findCommandRanges(value);
  const delimiterRanges = findSizedDelimiterRanges(value);
  const equationRanges = commandRanges
    .map((range) => equationRange(value, range, commandRanges))
    .filter((range): range is MathRange => Boolean(range));
  const atomRanges = commandRanges.map((range) => enclosingAtomRange(value, range));
  return mergeRanges([...delimiterRanges, ...equationRanges, ...atomRanges]);
}

function findSizedDelimiterRanges(value: string) {
  const ranges: MathRange[] = [];
  const openers: number[] = [];
  for (const match of value.matchAll(/\\+(left|right)\b/g)) {
    if (match.index === undefined) continue;
    if (match[1] === "left") {
      openers.push(match.index);
      continue;
    }
    const start = openers.pop();
    if (start !== undefined) {
      ranges.push({ start, end: sizedDelimiterEnd(value, match.index + match[0].length) });
    }
  }
  return ranges;
}

function sizedDelimiterEnd(value: string, commandEnd: number) {
  const delimiterStart = skipWhitespace(value, commandEnd);
  if (value[delimiterStart] !== "\\") return Math.min(value.length, delimiterStart + 1);
  const command = value.slice(delimiterStart).match(/^\\+[a-zA-Z]+/);
  return Math.min(value.length, delimiterStart + (command?.[0].length ?? 2));
}

function findCommandRanges(value: string) {
  const ranges: MathRange[] = [];
  for (const match of value.matchAll(/\\+[a-zA-Z]+/g)) {
    if (match.index === undefined) continue;
    ranges.push({ start: match.index, end: latexCommandEnd(value, match.index + match[0].length) });
  }
  return ranges;
}

function latexCommandEnd(value: string, initialEnd: number) {
  let end = initialEnd;
  while (end < value.length) {
    const whitespaceEnd = skipWhitespace(value, end);
    if (value[whitespaceEnd] === "{") {
      end = balancedGroupEnd(value, whitespaceEnd, "{", "}");
      continue;
    }
    if (value[whitespaceEnd] === "^" || value[whitespaceEnd] === "_") {
      end = scriptEnd(value, whitespaceEnd + 1);
      continue;
    }
    break;
  }
  return end;
}

function equationRange(value: string, command: MathRange, commands: MathRange[]) {
  const clauseStart = previousClauseBoundary(value, command.start);
  const clauseEnd = nextClauseBoundary(value, command.end);
  const relationIndex = topLevelRelationIndex(value, clauseStart, clauseEnd);
  if (relationIndex < 0) return null;
  const relatedCommands = commands.filter(
    ({ start, end }) => start < clauseEnd && end > clauseStart,
  );
  const leftCommands = relatedCommands.filter(({ start }) => start < relationIndex);
  const rightCommands = relatedCommands.filter(({ end }) => end > relationIndex);
  if (!leftCommands.length && !rightCommands.length) return null;

  const left = leftCommands.length
    ? enclosingAtomRange(value, leftCommands.at(-1)!).start
    : plainLeftOperandStart(value, relationIndex, clauseStart);
  const lastCommand = rightCommands.at(-1) ?? leftCommands.at(-1)!;
  const right = trailingFormulaEnd(value, enclosingAtomRange(value, lastCommand).end, clauseEnd);
  const candidate = value.slice(left, right);
  return containsProse(candidate) ? null : { start: left, end: right };
}

function topLevelRelationIndex(value: string, start: number, end: number) {
  const closers: string[] = [];
  const matchingCloser: Record<string, string> = { "{": "}", "(": ")", "[": "]" };
  for (let index = start; index < end; index += 1) {
    const character = value[index];
    if (character === "\\") {
      const command = value.slice(index).match(/^\\+[a-zA-Z]+/);
      if (command && closers.length === 0 && relationCommand(command[0])) return index;
      if (command) index += command[0].length - 1;
      continue;
    }
    if (character in matchingCloser) closers.push(matchingCloser[character]);
    else if (character === closers.at(-1)) closers.pop();
    else if (character === "=" && closers.length === 0) return index;
  }
  return -1;
}

function relationCommand(command: string) {
  return /^\\+(?:approx|equiv|geq?|leq?|in|sim)$/.test(command);
}

function enclosingAtomRange(value: string, range: MathRange): MathRange {
  const prefix = value.slice(0, range.start).match(/([a-zA-Z][a-zA-Z0-9_']*)[([]$/);
  if (!prefix) return range;
  const openerIndex = range.start - 1;
  const opener = value[openerIndex];
  const closer = opener === "(" ? ")" : "]";
  const end = balancedGroupEnd(value, openerIndex, opener, closer);
  if (end <= range.end) return range;
  return { start: range.start - prefix[0].length, end: consumeScripts(value, end) };
}

function balancedGroupEnd(value: string, start: number, opener: string, closer: string) {
  let depth = 0;
  for (let index = start; index < value.length; index += 1) {
    if (value[index] === opener && value[index - 1] !== "\\") depth += 1;
    if (value[index] === closer && value[index - 1] !== "\\") depth -= 1;
    if (depth === 0) return index + 1;
  }
  return value.length;
}

function scriptEnd(value: string, start: number) {
  const valueStart = skipWhitespace(value, start);
  if (value[valueStart] === "{") return balancedGroupEnd(value, valueStart, "{", "}");
  const command = value.slice(valueStart).match(/^\\+[a-zA-Z]+/);
  if (command) return latexCommandEnd(value, valueStart + command[0].length);
  return Math.min(value.length, valueStart + 1);
}

function consumeScripts(value: string, initialEnd: number) {
  let end = initialEnd;
  while (value[end] === "^" || value[end] === "_") end = scriptEnd(value, end + 1);
  return end;
}

function trailingFormulaEnd(value: string, initialEnd: number, clauseEnd: number) {
  let end = consumeScripts(value, initialEnd);
  while (end < clauseEnd && /[\s0-9a-zA-Z_^{},()[\]+*/|'-]/.test(value[end])) end += 1;
  return value.slice(0, end).trimEnd().length;
}

function previousClauseBoundary(value: string, before: number) {
  let start = 0;
  for (const match of value.slice(0, before).matchAll(/(?:^|[.!?;,:]\s+)/g)) {
    if (match.index !== undefined) start = match.index + match[0].length;
  }
  return start;
}

function nextClauseBoundary(value: string, after: number) {
  const match = value.slice(after).match(/[.!?;](?=\s|$)/);
  return match?.index === undefined ? value.length : after + match.index;
}

function plainLeftOperandStart(value: string, relation: number, floor: number) {
  const prefix = value.slice(floor, relation).trimEnd();
  const operand = prefix.match(/[a-zA-Z][a-zA-Z0-9_']*(?:[([][^\s]*[)\]])?$/);
  return operand?.index === undefined ? floor : floor + operand.index;
}

function containsProse(value: string) {
  const withoutLatex = value.replace(/\\+[a-zA-Z]+/g, "");
  return (withoutLatex.match(/\b[a-zA-Z][a-zA-Z'-]{2,}\b/g) ?? []).length >= 2;
}

function mergeRanges(ranges: MathRange[]) {
  const sorted = ranges.sort((left, right) => left.start - right.start || right.end - left.end);
  const merged: MathRange[] = [];
  for (const range of sorted) {
    const previous = merged.at(-1);
    if (previous && range.start <= previous.end) previous.end = Math.max(previous.end, range.end);
    else merged.push({ ...range });
  }
  return merged;
}

function skipWhitespace(value: string, start: number) {
  let end = start;
  while (/\s/.test(value[end] ?? "")) end += 1;
  return end;
}

function blockedMarkdownNode(node: MarkdownNode) {
  return ["code", "inlineCode", "math", "inlineMath"].includes(String(node.type || ""));
}

function inlineMathNode(value: string): MarkdownNode {
  return {
    type: "inlineMath",
    value,
    data: {
      hName: "code",
      hProperties: { className: ["language-math", "math-inline"] },
      hChildren: [textNode(value)],
    },
  };
}

function normalizeLooseLatex(value: string) {
  return value.replace(/\\+(?=[a-zA-Z])/g, "\\");
}

function textNode(value: string): MarkdownNode {
  return { type: "text", value };
}
