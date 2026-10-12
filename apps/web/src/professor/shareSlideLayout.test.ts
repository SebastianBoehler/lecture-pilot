import { describe, expect, it } from "vitest";

import { fitTitle, fitUrl, wrapUrl, wrapWords, type Measure } from "./shareSlideLayout";

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

  it("breaks links at slashes and long segments by character", () => {
    const lines = wrapUrl(
      measure,
      "https://lecturepilot.cs.uni-tuebingen.de/join/nlp/abcdefghijklmnopqrstuvwxyz0123456789",
      20,
      440,
    );
    expect(lines).toEqual([
      "lecturepilot.cs.uni-tuebingen.de/join/nlp",
      "/abcdefghijklmnopqrstuvwxyz0123456789",
    ]);
    expect(lines.join("")).toBe(
      "lecturepilot.cs.uni-tuebingen.de/join/nlp/abcdefghijklmnopqrstuvwxyz0123456789",
    );
    for (const line of lines) expect(measure(line, 20)).toBeLessThanOrEqual(440);
  });

  it("shrinks a long link to stay complete and drops it rather than truncate", () => {
    const url = `https://example.org/join/course/${"x".repeat(60)}`;
    expect(fitUrl(measure, url, 440, [{ size: 22, maxLines: 2 }])).toBeNull();
    const fitted = fitUrl(measure, url, 440, [
      { size: 22, maxLines: 2 },
      { size: 16, maxLines: 4 },
    ]);
    expect(fitted?.size).toBe(16);
    expect(fitted?.lines.join("")).toBe(url.replace("https://", ""));
  });
});
