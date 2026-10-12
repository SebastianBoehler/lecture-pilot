import type {
  PracticeDesign,
  PracticeDesignReadiness,
  PracticeDesignUpdate,
} from "./practiceDesignTypes";

export function updateFor(design: PracticeDesign): PracticeDesignUpdate {
  return {
    goals: design.learning_intent.goals,
    lecture_title: design.lecture_title,
    objective: design.objective,
    planning_context: design.planning_context,
    practice_design_revision: design.revision,
    source_revision: design.source_revision,
    targets: design.targets,
  };
}

export function isApproved(design: PracticeDesign) {
  const intent = design.learning_intent;
  return Boolean(
    intent.approval &&
    intent.source_revision === design.source_revision &&
    intent.approval.intent_revision === intent.revision,
  );
}

export function sameEditableDesign(left: PracticeDesign, right: PracticeDesign) {
  return JSON.stringify(updateFor(left)) === JSON.stringify(updateFor(right));
}

export function openLearningIntentIds(input: {
  lectureIds: readonly string[];
  designs: Readonly<Record<string, PracticeDesign>>;
  drafts: Readonly<Record<string, PracticeDesign>>;
  conflicts: Readonly<Record<string, boolean>>;
  readiness: Readonly<Record<string, PracticeDesignReadiness>>;
  pending: Readonly<Record<string, unknown>>;
}) {
  return input.lectureIds.filter((id) => {
    const design = input.designs[id];
    const draft = input.drafts[id];
    const current = input.readiness[id]?.current_source_revision;
    return Boolean(
      design &&
      !isApproved(design) &&
      !input.pending[id] &&
      !input.conflicts[id] &&
      (!draft || sameEditableDesign(design, draft)) &&
      (!current || current === design.source_revision),
    );
  });
}
