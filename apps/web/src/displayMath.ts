import katex from "katex";

import { katexOptions } from "./courseLatexMacros";

export type DisplayMathSegment = {
  kind: "math" | "prose";
  value: string;
};

export function segmentDisplayMath(expression: string): DisplayMathSegment[] {
  const trimmed = expression.trim();
  if (/^\\begin\{([a-zA-Z*]+)\}[\s\S]*\\end\{\1\}$/.test(trimmed)) {
    return [{ kind: "math", value: trimmed }];
  }
  return expression
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean)
    .flatMap(segmentDisplayLine);
}

export function tryRenderDisplayMath(expression: string) {
  try {
    return katex.renderToString(expression.replaceAll("...", "\\dots"), {
      ...katexOptions,
      displayMode: true,
      output: "html",
      throwOnError: true,
    });
  } catch {
    return null;
  }
}

export function delimitedMathIsRenderable(expression: string) {
  const normalized = expression
    .replace(/\\{1,2}\[([\s\S]*?)\\{1,2}\]/g, (_, formula: string) => `$$${formula}$$`)
    .replace(/\\{1,2}\(([\s\S]*?)\\{1,2}\)/g, (_, formula: string) => `$${formula}$`);
  for (const match of normalized.matchAll(/\$\$([\s\S]*?)\$\$|\$([^$\n]+)\$/g)) {
    if (!tryRenderDisplayMath(match[1] ?? match[2])) return false;
  }
  return true;
}

function segmentDisplayLine(value: string): DisplayMathSegment[] {
  const split = splitProsePrefix(value);
  if (split) {
    const suffix = splitFormulaSuffix(split.math);
    return [
      { kind: "prose", value: split.prose },
      { kind: "math", value: suffix.math },
      ...(suffix.prose ? segmentDisplayLine(suffix.prose) : []),
    ];
  }
  return [{ kind: looksLikeFormula(value) ? "math" : "prose", value }];
}

function splitProsePrefix(value: string) {
  const colon = value.match(/^(.+?):\s+(.+)$/);
  if (colon && isPlainProsePrefix(colon[1]) && looksLikeFormula(colon[2])) {
    return { prose: `${colon[1]}:`, math: colon[2] };
  }

  const relationIndex = value.search(/=|\\(?:approx|equiv|geq?|leq?|in|sim)\b/);
  if (relationIndex <= 0) return null;
  const left = value.slice(0, relationIndex);
  const atom = left.match(/\S+\s*$/);
  if (!atom || atom.index === undefined) return null;
  const prose = left.slice(0, atom.index).trim();
  if (!isPlainProsePrefix(prose)) return null;
  return { prose, math: value.slice(atom.index).trim() };
}

function splitFormulaSuffix(value: string) {
  const boundary = findProseBoundary(value);
  if (!boundary) return { math: value, prose: "" };
  return {
    math: value.slice(0, boundary.mathEnd).trim(),
    prose: value.slice(boundary.proseStart).trim(),
  };
}

function findProseBoundary(value: string) {
  let depth = 0;
  for (let index = 0; index < value.length; index += 1) {
    const character = value[index];
    if ("{([".includes(character)) depth += 1;
    if ("})]".includes(character)) depth = Math.max(0, depth - 1);
    if (depth || value[index - 1] === "\\") continue;
    const continuation = value
      .slice(index)
      .match(/^(\s+)(?:where|when|because|which|so that|such that)\b/i);
    if (continuation && /=|\\(?:approx|equiv|geq?|leq?|in|sim)\b/.test(value.slice(0, index))) {
      return {
        mathEnd: index,
        proseStart: index + continuation[1].length,
      };
    }
    if (!".,;".includes(character)) continue;
    const following = value.slice(index + 1).match(/^(\s+)([a-zA-Z][a-zA-Z'-]{2,})\b/);
    if (!following) continue;
    if (character === "." && !/^[A-Z]/.test(following[2])) continue;
    return {
      mathEnd: index + 1,
      proseStart: index + 1 + following[1].length,
    };
  }
  return null;
}

function looksLikeFormula(value: string) {
  if (/=|\\(?:approx|equiv|geq?|leq?|in|sim)\b/.test(value)) return true;
  const withoutCommands = value.replace(/\\[a-zA-Z]+/g, "");
  if (looksLikeProse(withoutCommands)) return false;
  return /[<>_^{}]|\\[a-zA-Z]+|[∑∫√≈≤≥]/.test(value);
}

function looksLikeProse(value: string) {
  return (value.match(/\b[a-zA-Z][a-zA-Z'-]{2,}\b/g) ?? []).length >= 2;
}

function isPlainProsePrefix(value: string) {
  return !/[\\$^_{}=<>]/.test(value) && /\b[a-zA-Z][a-zA-Z'-]+\b/.test(value);
}
