import { describe, expect, it } from "vitest";

import {
  collapseUnchanged,
  diffCanvasSections,
  diffUnits,
  sectionUnits,
} from "./canvasSectionDiff";
import type { CanvasBlock, CanvasDocument, CanvasSection } from "../shared/types";

const block = (id: string, patch: Partial<CanvasBlock>): CanvasBlock => ({
  id,
  type: "paragraph",
  items: [],
  ...patch,
});
const section = (id: string, title: string, texts: string[]): CanvasSection => ({
  id,
  title,
  blocks: texts.map((text, index) => block(`${id}-${index}`, { text })),
});
const canvas = (sections: CanvasSection[]): CanvasDocument => ({
  id: "canvas",
  course_id: "ml",
  lecture_id: "lecture-02",
  title: "Gradient Descent",
  source_kind: "generated",
  source_ref: "source",
  sections,
});

describe("diffUnits", () => {
  it("keeps common paragraphs and marks removals before additions", () => {
    expect(diffUnits(["a", "b", "c"], ["a", "x", "c", "d"])).toEqual([
      { kind: "same", text: "a" },
      { kind: "removed", text: "b" },
      { kind: "added", text: "x" },
      { kind: "same", text: "c" },
      { kind: "added", text: "d" },
    ]);
  });

  it("handles empty sides", () => {
    expect(diffUnits([], ["a"])).toEqual([{ kind: "added", text: "a" }]);
    expect(diffUnits(["a"], [])).toEqual([{ kind: "removed", text: "a" }]);
  });
});

describe("sectionUnits", () => {
  it("turns learning blocks into readable paragraphs", () => {
    const units = sectionUnits({
      id: "s",
      title: "S",
      blocks: [
        block("p", { text: "First.\n\nSecond." }),
        block("l", { type: "list", items: ["one", "two"] }),
        block("m", { type: "math", text: "x^2" }),
        block("q", { type: "quiz", text: "Pick one", items: ["A", "B"] }),
        block("c", { type: "checkpoint", text: "Explain it" }),
        block("a", { type: "asset", caption: "A figure" }),
      ],
    });
    expect(units).toEqual([
      "First.",
      "Second.",
      "- one\n- two",
      "$$\nx^2\n$$",
      "**Quiz:** Pick one\n- A\n- B",
      "**Checkpoint:** Explain it",
      "**Figure:** A figure",
    ]);
  });
});

describe("diffCanvasSections", () => {
  it("reports added, removed, changed and unchanged sections in draft order", () => {
    const published = canvas([
      section("intro", "Introduction", ["Hello"]),
      section("steps", "Steps", ["Step one", "Step two"]),
      section("old", "Old part", ["Gone"]),
    ]);
    const draft = canvas([
      section("intro", "Introduction", ["Hello"]),
      section("steps", "Steps", ["Step one", "Step two, revised"]),
      section("new", "New part", ["Fresh"]),
    ]);
    const diff = diffCanvasSections(published, draft);
    expect(diff.map(({ kind, title }) => [kind, title])).toEqual([
      ["unchanged", "Introduction"],
      ["changed", "Steps"],
      ["added", "New part"],
      ["removed", "Old part"],
    ]);
    expect(diff[1].units).toEqual([
      { kind: "same", text: "Step one" },
      { kind: "removed", text: "Step two" },
      { kind: "added", text: "Step two, revised" },
    ]);
  });

  it("matches regenerated section ids by title and reports title changes", () => {
    const byTitle = diffCanvasSections(
      canvas([section("a", "Same title", ["x"])]),
      canvas([section("b", "Same title", ["x"])]),
    );
    expect(byTitle.map(({ kind }) => kind)).toEqual(["unchanged"]);
    const renamed = diffCanvasSections(
      canvas([section("a", "Old title", ["x"])]),
      canvas([section("a", "New title", ["x"])]),
    );
    expect(renamed[0]).toMatchObject({
      kind: "changed",
      title: "New title",
      previousTitle: "Old title",
    });
  });

  it("treats every section as added when nothing is published yet", () => {
    expect(diffCanvasSections(null, canvas([section("a", "A", ["x"])]))[0].kind).toBe("added");
  });
});

describe("collapseUnchanged", () => {
  it("keeps one paragraph of context around changes", () => {
    const units = diffUnits(["a", "b", "c", "d", "e"], ["a", "b", "c", "d", "E"]);
    expect(collapseUnchanged(units)).toEqual([
      {
        kind: "skipped",
        units: [
          { kind: "same", text: "a" },
          { kind: "same", text: "b" },
          { kind: "same", text: "c" },
        ],
      },
      { kind: "same", text: "d" },
      { kind: "removed", text: "e" },
      { kind: "added", text: "E" },
    ]);
  });

  it("folds trailing runs and keeps the hidden paragraphs for expansion", () => {
    const units = diffUnits(["x", "a", "b", "c"], ["X", "a", "b", "c"]);
    expect(collapseUnchanged(units).map((unit) => unit.kind)).toEqual([
      "removed",
      "added",
      "same",
      "skipped",
    ]);
    expect(collapseUnchanged(units).at(-1)).toEqual({
      kind: "skipped",
      units: [
        { kind: "same", text: "b" },
        { kind: "same", text: "c" },
      ],
    });
  });
});
