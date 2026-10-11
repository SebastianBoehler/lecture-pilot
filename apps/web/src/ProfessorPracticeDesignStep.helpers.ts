import type {
  PracticeDesign,
  PracticeDesignReadiness,
  PracticeDesignUpdate,
} from "./practiceDesignTypes";

export function updateFor(design: PracticeDesign): PracticeDesignUpdate {
  return {
    ...(design.learning_intent ? { goals: design.learning_intent.goals } : {}),
    lecture_title: design.lecture_title,
    objective: design.objective,
    planning_context: design.planning_context,
    practice_design_revision: design.revision,
    source_revision: design.source_revision,
    targets: design.targets,
  };
}

export function isApproved(design: PracticeDesign) {
  return Boolean(
    (!design.approval &&
      design.learning_intent?.approval &&
      design.learning_intent.source_revision === design.source_revision &&
      design.learning_intent.approval.intent_revision === design.learning_intent.revision) ||
    (design.approval &&
      design.approval.source_revision === design.source_revision &&
      design.approval.practice_design_revision === design.revision),
  );
}

export function sameEditableDesign(left: PracticeDesign, right: PracticeDesign) {
  return JSON.stringify(updateFor(left)) === JSON.stringify(updateFor(right));
}

export function currentQualityReview(design: PracticeDesign) {
  const review = design.quality_review;
  return review &&
    review.source_revision === design.source_revision &&
    review.practice_design_revision === design.revision
    ? review
    : null;
}

export function hasCriticalQualityFinding(design: PracticeDesign) {
  return Boolean(
    currentQualityReview(design)?.checks.some((check) => check.severity === "critical"),
  );
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
      design?.learning_intent &&
      !design.approval &&
      !isApproved(design) &&
      !input.pending[id] &&
      !input.conflicts[id] &&
      (!draft || sameEditableDesign(design, draft)) &&
      (!current || current === design.source_revision),
    );
  });
}
