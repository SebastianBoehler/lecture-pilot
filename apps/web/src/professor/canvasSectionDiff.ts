import type { CanvasBlock, CanvasDocument, CanvasSection } from "../shared/types";

export type UnitDiff = Readonly<{ kind: "same" | "added" | "removed"; text: string }>;
export type SkippedUnits<T> = Readonly<{ kind: "skipped"; units: readonly T[] }>;

export type SectionDiff = Readonly<{
  kind: "added" | "removed" | "changed" | "unchanged";
  id: string;
  title: string;
  previousTitle?: string;
  units: readonly UnitDiff[];
}>;

/** Larger sections fall back to a whole-section replacement instead of a quadratic diff. */
const MAX_DIFF_CELLS = 250_000;

/**
 * Section-level comparison of the published canvas with a draft. Sections match by id first and
 * then by title (regenerated drafts may renumber ids); results follow draft order, removed last.
 */
export function diffCanvasSections(
  published: CanvasDocument | null,
  draft: CanvasDocument,
): SectionDiff[] {
  const remaining = [...(published?.sections ?? [])];
  const matches = new Map<CanvasSection, CanvasSection>();
  const take = (predicate: (section: CanvasSection) => boolean) => {
    const index = remaining.findIndex(predicate);
    return index < 0 ? undefined : remaining.splice(index, 1)[0];
  };
  for (const section of draft.sections) {
    const match = take((candidate) => candidate.id === section.id);
    if (match) matches.set(section, match);
  }
  for (const section of draft.sections) {
    if (matches.has(section)) continue;
    const match = take((candidate) => sameTitle(candidate.title, section.title));
    if (match) matches.set(section, match);
  }
  const compared = draft.sections.map((section): SectionDiff => {
    const before = matches.get(section);
    const after = sectionUnits(section);
    if (!before) {
      return { kind: "added", id: section.id, title: section.title, units: added(after) };
    }
    const units = diffUnits(sectionUnits(before), after);
    const titleChanged = before.title !== section.title;
    const changed = titleChanged || units.some((unit) => unit.kind !== "same");
    return {
      kind: changed ? "changed" : "unchanged",
      id: section.id,
      title: section.title,
      ...(titleChanged ? { previousTitle: before.title } : {}),
      units,
    };
  });
  return [
    ...compared,
    ...remaining.map((section): SectionDiff => ({
      kind: "removed",
      id: section.id,
      title: section.title,
      units: sectionUnits(section).map((text) => ({ kind: "removed", text })),
    })),
  ];
}

/** Readable paragraph units of a section; paragraphs split on blank lines. */
export function sectionUnits(section: CanvasSection): string[] {
  return section.blocks.flatMap(blockUnits).filter((unit) => unit.length > 0);
}

function blockUnits(block: CanvasBlock): string[] {
  const text = block.text?.trim() ?? "";
  const items = block.items.map((item) => `- ${item}`).join("\n");
  switch (block.type) {
    case "paragraph":
    case "callout":
      return text.split(/\n\s*\n/).map((part) => part.trim());
    case "list":
      return [items];
    case "math":
      return [`$$\n${text}\n$$`];
    case "quiz":
      return [[`**Quiz:** ${text}`, items].filter(Boolean).join("\n")];
    case "checkpoint":
      return [`**Checkpoint:** ${text}`];
    case "prediction":
      return [`**Prediction:** ${text}`];
    case "asset":
      return [`**Figure:** ${block.caption ?? block.asset_path ?? ""}`.trim()];
    case "video":
      return [`**Video:** ${block.caption ?? text}`.trim()];
    case "component":
      return [`**Interactive:** ${block.caption ?? block.component_type ?? ""}`.trim()];
    case "table":
      return [text];
  }
}

/** Longest-common-subsequence diff; removals precede additions at each change. */
export function diffUnits(before: readonly string[], after: readonly string[]): UnitDiff[] {
  if (before.length * after.length > MAX_DIFF_CELLS) {
    return [...before.map((text) => ({ kind: "removed" as const, text })), ...added(after)];
  }
  const rows = before.length + 1;
  const cols = after.length + 1;
  const table = new Uint32Array(rows * cols);
  for (let i = before.length - 1; i >= 0; i -= 1) {
    for (let j = after.length - 1; j >= 0; j -= 1) {
      table[i * cols + j] =
        before[i] === after[j]
          ? table[(i + 1) * cols + j + 1] + 1
          : Math.max(table[(i + 1) * cols + j], table[i * cols + j + 1]);
    }
  }
  const result: UnitDiff[] = [];
  let i = 0;
  let j = 0;
  while (i < before.length || j < after.length) {
    if (i < before.length && j < after.length && before[i] === after[j]) {
      result.push({ kind: "same", text: before[i] });
      i += 1;
      j += 1;
    } else if (
      i < before.length &&
      (j >= after.length || table[(i + 1) * cols + j] >= table[i * cols + j + 1])
    ) {
      result.push({ kind: "removed", text: before[i] });
      i += 1;
    } else {
      result.push({ kind: "added", text: after[j] });
      j += 1;
    }
  }
  return result;
}

/** Folds runs of unchanged paragraphs, keeping `context` paragraphs next to each change. */
export function collapseUnchanged<T extends Readonly<{ kind: string }>>(
  units: readonly T[],
  context = 1,
): (T | SkippedUnits<T>)[] {
  const result: (T | SkippedUnits<T>)[] = [];
  let hidden: T[] = [];
  units.forEach((unit, index) => {
    const nearChange = units
      .slice(Math.max(0, index - context), index + context + 1)
      .some((near) => near.kind !== "same");
    if (!nearChange) {
      hidden.push(unit);
      return;
    }
    if (hidden.length) result.push({ kind: "skipped", units: hidden });
    hidden = [];
    result.push(unit);
  });
  if (hidden.length) result.push({ kind: "skipped", units: hidden });
  return result;
}

function added(units: readonly string[]): UnitDiff[] {
  return units.map((text) => ({ kind: "added", text }));
}

function sameTitle(left: string, right: string) {
  return left.trim().toLocaleLowerCase() === right.trim().toLocaleLowerCase();
}
