import type { UnitDiff } from "../canvasSectionDiff";
import { diffWords, isProseUnit, wordSimilarity, type WordSegment } from "./wordDiff";

export type SectionShape = "edited" | "rewritten";

export type EditedUnit = Readonly<{ kind: "edited"; words: readonly WordSegment[] }>;
export type DisplayUnit = UnitDiff | EditedUnit;

/** Below this word overlap a replaced paragraph is shown whole instead of word by word. */
const PARAGRAPH_EDIT_SIMILARITY = 0.5;
/** Below this word overlap a section with mostly replaced paragraphs counts as rewritten. */
const SECTION_EDIT_SIMILARITY = 0.7;

/**
 * A section is lightly edited when at least half of its paragraphs survive unchanged or most of its
 * words do; otherwise it was rewritten and reads better as "before | after" than as interleaved
 * removals.
 */
export function sectionShape(units: readonly UnitDiff[]): SectionShape {
  const before = units.filter((unit) => unit.kind !== "added").map((unit) => unit.text);
  const after = units.filter((unit) => unit.kind !== "removed").map((unit) => unit.text);
  const kept = units.filter((unit) => unit.kind === "same").length;
  if (kept * 2 >= Math.max(before.length, after.length)) return "edited";
  return wordSimilarity(before.join("\n"), after.join("\n")) >= SECTION_EDIT_SIMILARITY
    ? "edited"
    : "rewritten";
}

/**
 * Pairs each removed paragraph with the added paragraph at the same position of its change run.
 * Similar prose pairs become one word-level edit; the rest stay as whole removals and additions,
 * each replaced paragraph directly followed by its replacement.
 */
export function pairEdits(units: readonly UnitDiff[]): DisplayUnit[] {
  const result: DisplayUnit[] = [];
  let index = 0;
  while (index < units.length) {
    if (units[index].kind === "same") {
      result.push(units[index]);
      index += 1;
      continue;
    }
    const removed: UnitDiff[] = [];
    const added: UnitDiff[] = [];
    for (; index < units.length && units[index].kind !== "same"; index += 1) {
      (units[index].kind === "removed" ? removed : added).push(units[index]);
    }
    for (let pair = 0; pair < Math.max(removed.length, added.length); pair += 1) {
      const before = removed[pair];
      const after = added[pair];
      if (before && after && isEdit(before.text, after.text)) {
        result.push({ kind: "edited", words: diffWords(before.text, after.text) });
        continue;
      }
      if (before) result.push(before);
      if (after) result.push(after);
    }
  }
  return result;
}

function isEdit(before: string, after: string) {
  return (
    isProseUnit(before) &&
    isProseUnit(after) &&
    wordSimilarity(before, after) >= PARAGRAPH_EDIT_SIMILARITY
  );
}
