import { expect, it } from "vitest";
import { teachingLanguageOverlay } from "./teachingLanguageOverlay";
import type { CanvasDocument } from "./types";

it("changes canonical teaching only, preserving assessments and learner edits", () => {
  const document: CanvasDocument = {
    id: "doc",
    course_id: "course",
    lecture_id: "lecture",
    title: "Title",
    source_kind: "markdown",
    source_ref: "source",
    sections: [
      {
        id: "section",
        title: "Section",
        blocks: [
          { id: "text", type: "paragraph", text: "Explanation", items: [] },
          { id: "check", type: "checkpoint", text: "Exact assessment", items: [] },
          { id: "student", type: "paragraph", text: "My personal change", items: [] },
        ],
      },
    ],
  };
  const originals = [
    { key: "block:section:text:text", text: "Explanation" },
    { key: "block:section:check:text", text: "Exact assessment" },
    { key: "block:section:student:text", text: "Old teaching" },
  ];
  const translated = teachingLanguageOverlay(
    document,
    {
      language: "de",
      digest: "digest",
      publication_version: 1,
      published_at: "now",
      texts: originals.map((text) => ({ ...text, text: "Übersetzung" })),
    },
    originals,
  );
  expect(translated.sections[0].blocks.map((block) => block.text)).toEqual([
    "Übersetzung",
    "Exact assessment",
    "My personal change",
  ]);
  expect(document.sections[0].blocks[0].text).toBe("Explanation");
});
