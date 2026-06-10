import { expect, it } from "vitest";

import { sectionSourceReferences } from "./sourceReferences";
import type { CanvasDocument, CanvasSection } from "./types";

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
