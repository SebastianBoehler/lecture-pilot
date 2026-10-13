import { describe, expect, it } from "vitest";

import {
  diffWords,
  escapeLeadingBlockMarker,
  isProseUnit,
  wordSimilarity,
  wordTokens,
} from "./wordDiff";

describe("wordTokens", () => {
  it("keeps math, code, bold spans and links whole", () => {
    expect(
      wordTokens("Step $\\nabla L(\\theta)$ uses `lr` and **two words** [see](https://x.y)."),
    ).toEqual([
      "Step",
      " ",
      "$\\nabla L(\\theta)$",
      " ",
      "uses",
      " ",
      "`lr`",
      " ",
      "and",
      " ",
      "**two words**",
      " ",
      "[see](https://x.y)",
      ".",
    ]);
  });
});

describe("diffWords", () => {
  it("marks only the changed words", () => {
    expect(diffWords("The quick fox runs.", "The slow fox runs.")).toEqual([
      { kind: "same", text: "The " },
      { kind: "removed", text: "quick" },
      { kind: "added", text: "slow" },
      { kind: "same", text: " fox runs." },
    ]);
  });

  it("joins a rewritten phrase into one removal and one addition", () => {
    expect(diffWords("We take a small step here.", "We move by eta each time here.")).toEqual([
      { kind: "same", text: "We " },
      { kind: "removed", text: "take a small step" },
      { kind: "added", text: "move by eta each time" },
      { kind: "same", text: " here." },
    ]);
  });

  it("treats a changed formula as one unit", () => {
    expect(diffWords("Update $w$ now.", "Update $w_t$ now.")).toEqual([
      { kind: "same", text: "Update " },
      { kind: "removed", text: "$w$" },
      { kind: "added", text: "$w_t$" },
      { kind: "same", text: " now." },
    ]);
  });

  it("reports pure insertions and deletions", () => {
    expect(diffWords("a c", "a b c")).toEqual([
      { kind: "same", text: "a " },
      { kind: "added", text: "b" },
      { kind: "same", text: " c" },
    ]);
    expect(diffWords("a b c", "a c")).toEqual([
      { kind: "same", text: "a " },
      { kind: "removed", text: "b" },
      { kind: "same", text: " c" },
    ]);
  });
});

describe("wordSimilarity", () => {
  it("scores shared words between 0 and 1", () => {
    expect(wordSimilarity("", "")).toBe(1);
    expect(wordSimilarity("a b", "c d")).toBe(0);
    expect(wordSimilarity("The Gradient step", "the gradient step")).toBe(1);
    expect(wordSimilarity("a b c d", "a b x y")).toBe(0.5);
  });
});

describe("isProseUnit", () => {
  it("rejects lists, tables, display math and code fences", () => {
    expect(isProseUnit("A plain paragraph with $x$.")).toBe(true);
    expect(isProseUnit("- one\n- two")).toBe(false);
    expect(isProseUnit("| a | b |\n| - | - |")).toBe(false);
    expect(isProseUnit("$$\nx^2\n$$")).toBe(false);
    expect(isProseUnit("```math\nx\n```")).toBe(false);
  });
});

describe("escapeLeadingBlockMarker", () => {
  it("keeps a lone segment inline", () => {
    expect(escapeLeadingBlockMarker("- b")).toBe("\\- b");
    expect(escapeLeadingBlockMarker("# 1")).toBe("\\# 1");
    expect(escapeLeadingBlockMarker("2. Then")).toBe("2\\. Then");
    expect(escapeLeadingBlockMarker("---")).toBe("\\---");
    expect(escapeLeadingBlockMarker("> quote")).toBe("\\> quote");
    expect(escapeLeadingBlockMarker("**bold** text")).toBe("**bold** text");
    expect(escapeLeadingBlockMarker("plain")).toBe("plain");
  });
});
