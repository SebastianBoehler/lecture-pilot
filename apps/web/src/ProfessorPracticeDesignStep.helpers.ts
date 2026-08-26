import type { PracticeDesign, PracticeDesignUpdate } from "./practiceDesignTypes";

export function updateFor(design: PracticeDesign): PracticeDesignUpdate {
  return {
    lecture_title: design.lecture_title,
    objective: design.objective,
    practice_design_revision: design.revision,
    source_revision: design.source_revision,
    targets: design.targets,
  };
}

export function isApproved(design: PracticeDesign) {
  return Boolean(
    design.approval &&
    design.approval.source_revision === design.source_revision &&
    design.approval.practice_design_revision === design.revision,
  );
}

export function sameEditableDesign(left: PracticeDesign, right: PracticeDesign) {
  return JSON.stringify(updateFor(left)) === JSON.stringify(updateFor(right));
}
