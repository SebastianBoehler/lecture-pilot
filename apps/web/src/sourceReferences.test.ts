import { expect, it } from "vitest";

import { sectionSourceReferences } from "./sourceReferences";
import type { CanvasDocument } from "./types";

it("shows the underlying lecture file for generated course-planner canvases", () => {
  const references = sectionSourceReferences(generatedCanvas(), {
    id: "losses-and-risks",
    title: "Losses and risks",
    source_ref: "Lecture03-eng.tex, frames 33-38",
    blocks: [],
  });

  expect(references[0].resource.path).toBe("Lecture03-eng.tex");
  expect(references[0].resource.detail).toBe("frames 33-38");
});

it("turns multi-file provenance into separate readable references", () => {
  const references = sectionSourceReferences(generatedCanvas(), {
    id: "bird-family-tree",
    title: "Bird family tree",
    source_ref:
      "uploads/gml-upload/Lecture08-eng.tex frames 5, 8, 9; " +
      "uploads/gml-upload/Lecture08-audio.txt (paragraphs 5-6)",
    blocks: [],
  });

  expect(references.map((reference) => reference.resource.label)).toEqual([
    "Lecture08-eng.tex",
    "Lecture08-audio.txt",
  ]);
  expect(references.map((reference) => reference.resource.path)).toEqual([
    "uploads/gml-upload/Lecture08-eng.tex",
    "uploads/gml-upload/Lecture08-audio.txt",
  ]);
  expect(references.map((reference) => reference.resource.detail)).toEqual([
    "frames 5, 8, 9",
    "paragraphs 5-6",
  ]);
});

it("keeps course-media paths in the inspector but shows a readable filename", () => {
  const references = sectionSourceReferences(generatedCanvas(), {
    id: "bird-family-tree",
    title: "Bird family tree",
    source_ref: "uploads/gml-upload/Lecture08-eng.tex frames 5-9",
    blocks: [
      {
        id: "bird-tree",
        type: "asset",
        asset_path: "uploads/gml-upload/images/Ch8/bird-family-tree.png",
        caption: "Bird family tree",
        items: [],
      },
    ],
  });

  expect(references[1].resource.label).toBe("bird-family-tree.png");
  expect(references[1].resource.path).toBe("uploads/gml-upload/images/Ch8/bird-family-tree.png");
});

function generatedCanvas(): CanvasDocument {
  return {
    id: "martius-ml-lecture-03",
    import_version: 1,
    course_id: "martius-ml",
    lecture_id: "lecture-03",
    title: "Bayesian Decision Theory",
    source_kind: "generated",
    source_ref: "course planner from Lecture03-eng.tex",
    workspace_path: "canvas/index.md",
    sections: [],
  };
}
