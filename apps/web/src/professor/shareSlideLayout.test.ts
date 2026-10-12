import { describe, expect, it } from "vitest";

import { fitTitle, wrapWords, type Measure } from "./shareSlideLayout";

// Every character is half the font size wide.
const measure: Measure = (text, size) => text.length * size * 0.5;

describe("share slide layout", () => {
  it("wraps words within the available width", () => {
    expect(wrapWords(measure, "Natural Language Processing", 10, 70)).toEqual([
      "Natural",
      "Language",
      "Processing",
    ]);
  });

  it("uses the largest title size that fits the line and height budget", () => {
    const fitted = fitTitle(measure, "Natural Language Processing", {
      maxWidth: 760,
      maxHeight: 230,
      maxLines: 3,
      sizes: [84, 72, 64, 56],
    });
    expect(fitted).toEqual({ size: 84, lines: ["Natural Language", "Processing"] });
  });

  it("shrinks long titles and ellipsizes only when even the smallest size overflows", () => {
    const long = Array.from({ length: 40 }, (_, index) => `Word${index}`).join(" ");
    const fitted = fitTitle(measure, long, {
      maxWidth: 400,
      maxHeight: 230,
      maxLines: 3,
      sizes: [84, 56],
    });
    expect(fitted.size).toBe(56);
    expect(fitted.lines).toHaveLength(3);
    expect(fitted.lines[2].endsWith("…")).toBe(true);
    for (const line of fitted.lines) expect(measure(line, 56)).toBeLessThanOrEqual(400);
  });
});
