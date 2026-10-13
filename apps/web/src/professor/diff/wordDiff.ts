import { diffUnits } from "../canvasSectionDiff";

export type WordSegment = Readonly<{ kind: "same" | "added" | "removed"; text: string }>;

/**
 * Words, whitespace and atomic Markdown spans. Math, inline code, bold spans and links stay whole
 * so a changed word never splits LaTeX or emphasis markup across rendered segments.
 */
const TOKEN =
  /\$\$[\s\S]*?\$\$|\$[^$\n]+\$|`[^`\n]+`|\*\*[^*\n]+\*\*|\[[^\]\n]*\]\([^)\s]*\)|\S+|\s+/g;

/** Block syntax that a per-segment inline render would misread. */
const BLOCK_SYNTAX = /```|\$\$|^\s*(?:[-*+>|#]|\d+[.)])\s/m;

export function wordTokens(text: string): string[] {
  return text.match(TOKEN) ?? [];
}

/** Single prose paragraphs can be compared word by word; lists, tables and display math cannot. */
export function isProseUnit(text: string): boolean {
  return !BLOCK_SYNTAX.test(text);
}

/**
 * Word-level diff of two prose paragraphs. Changes separated only by spaces form one removed run
 * followed by one added run, so a rewritten phrase reads as "old phrase → new phrase".
 */
export function diffWords(before: string, after: string): WordSegment[] {
  const units = diffUnits(wordTokens(before), wordTokens(after));
  const segments: WordSegment[] = [];
  let index = 0;
  while (index < units.length) {
    if (units[index].kind === "same") {
      pushMerged(segments, units[index]);
      index += 1;
      continue;
    }
    let removed = "";
    let added = "";
    let space = { removed: "", added: "" };
    for (; index < units.length; index += 1) {
      const { kind, text } = units[index];
      if (kind === "removed") {
        removed += space.removed + text;
        space = { ...space, removed: "" };
      } else if (kind === "added") {
        added += space.added + text;
        space = { ...space, added: "" };
      } else if (!text.trim() && units[index + 1] && units[index + 1].kind !== "same") {
        space = { removed: removed ? text : "", added: added ? text : "" };
      } else break;
    }
    const tail = (added || removed).match(/\s+$/)?.[0] ?? "";
    if (removed.trimEnd()) segments.push({ kind: "removed", text: removed.trimEnd() });
    if (added.trimEnd()) segments.push({ kind: "added", text: added.trimEnd() });
    if (tail && index < units.length) pushMerged(segments, { kind: "same", text: tail });
  }
  return segments;
}

function pushMerged(segments: WordSegment[], segment: WordSegment) {
  const last = segments.at(-1);
  if (last?.kind === segment.kind) {
    segments[segments.length - 1] = { kind: last.kind, text: last.text + segment.text };
  } else segments.push(segment);
}

/** Bag-of-words Dice coefficient in [0, 1]; two empty texts are identical. */
export function wordSimilarity(before: string, after: string): number {
  const left = words(before);
  const right = words(after);
  if (!left.length && !right.length) return 1;
  const counts = new Map<string, number>();
  for (const word of left) counts.set(word, (counts.get(word) ?? 0) + 1);
  let shared = 0;
  for (const word of right) {
    const count = counts.get(word) ?? 0;
    if (count > 0) {
      shared += 1;
      counts.set(word, count - 1);
    }
  }
  return (2 * shared) / (left.length + right.length);
}

/**
 * Keeps a segment that starts with block syntax (`-`, `#`, `1.`) inline when rendered alone, by
 * escaping that first marker.
 */
export function escapeLeadingBlockMarker(text: string): string {
  const ordered = text.match(/^(\d+)([.)])/);
  if (ordered) return `${ordered[1]}\\${text.slice(ordered[1].length)}`;
  return /^(?:>|[-*+#=_|]+(?=\s|$))/.test(text) ? `\\${text}` : text;
}

function words(text: string): string[] {
  return text.toLocaleLowerCase().match(/[\p{L}\p{N}\\]+/gu) ?? [];
}
