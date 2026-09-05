import type { LearnerLessonState } from "./learnerLessonStateTypes";
import type { CanvasDocument } from "./types";

export function canvasWithPendingCheck(
  document: CanvasDocument,
  pending: LearnerLessonState["pending_check"] | undefined,
): CanvasDocument {
  if (!pending) return document;
  return {
    ...document,
    sections: document.sections.map((section) => ({
      ...section,
      blocks: section.blocks.map((block) =>
        block.type === "checkpoint" && block.id === pending.gate_id
          ? { ...block, text: pending.prompt }
          : block,
      ),
    })),
  };
}
