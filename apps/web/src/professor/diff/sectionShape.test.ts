import { describe, expect, it } from "vitest";

import { diffUnits } from "../canvasSectionDiff";
import { pairEdits, sectionShape } from "./sectionShape";

describe("sectionShape", () => {
  it("treats a section that keeps most paragraphs as edited", () => {
    expect(sectionShape(diffUnits(["a", "b", "c", "d"], ["a", "b", "c", "x"]))).toBe("edited");
  });

  it("treats small wording changes in every paragraph as edited", () => {
    const before = ["The step size is small.", "Gradients point uphill fast."];
    const after = ["The step size is tiny.", "Gradients point uphill quickly."];
    expect(sectionShape(diffUnits(before, after))).toBe("edited");
  });

  it("treats a regenerated section as rewritten", () => {
    const before = ["Momentum keeps velocity.", "It smooths noisy updates.", "Use beta 0.9."];
    const after = ["Adam adapts the learning rate.", "Each weight gets its own scale."];
    expect(sectionShape(diffUnits(before, after))).toBe("rewritten");
  });

  it("keeps title-only changes edited", () => {
    expect(sectionShape(diffUnits(["a"], ["a"]))).toBe("edited");
    expect(sectionShape([])).toBe("edited");
  });
});

describe("pairEdits", () => {
  it("turns a similar replacement into a word-level edit", () => {
    expect(
      pairEdits(diffUnits(["Keep.", "The step is small."], ["Keep.", "The step is tiny."])),
    ).toEqual([
      { kind: "same", text: "Keep." },
      {
        kind: "edited",
        words: [
          { kind: "same", text: "The step is " },
          { kind: "removed", text: "small." },
          { kind: "added", text: "tiny." },
        ],
      },
    ]);
  });

  it("keeps unrelated replacements whole and places each before its replacement", () => {
    expect(
      pairEdits(diffUnits(["One old.", "Two old."], ["Brand new.", "Fresh again.", "x"])),
    ).toEqual([
      { kind: "removed", text: "One old." },
      { kind: "added", text: "Brand new." },
      { kind: "removed", text: "Two old." },
      { kind: "added", text: "Fresh again." },
      { kind: "added", text: "x" },
    ]);
  });

  it("never word-diffs lists or display math", () => {
    const units = pairEdits(diffUnits(["- a\n- b"], ["- a\n- c"]));
    expect(units.map((unit) => unit.kind)).toEqual(["removed", "added"]);
  });
});
