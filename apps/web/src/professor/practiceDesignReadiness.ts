import type { PracticeDesign, PracticeDesignReadiness } from "./practiceDesignTypes";

export function isPracticeDesignReady(
  design: PracticeDesign | undefined,
  readiness: PracticeDesignReadiness | undefined,
) {
  return Boolean(
    design &&
    readiness?.ready_for_generation &&
    readiness.lecture_id === design.lecture_id &&
    readiness.current_source_revision === design.source_revision &&
    readiness.practice_design_revision === design.revision,
  );
}
