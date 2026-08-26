import type {
  PracticeDesign,
  PracticeDesignQualityReview,
  PracticeDesignReviewCheck,
  PracticeReviewDimension,
} from "./practiceDesignTypes";

const REVIEW_DIMENSIONS: readonly PracticeReviewDimension[] = [
  "source_entailment",
  "objective_task_alignment",
  "exit_equivalence",
  "answer_leakage",
  "difficulty_drift",
  "transfer_invariant_novelty",
  "rubric_sufficiency",
  "target_source_coverage",
];

type FixtureOptions = {
  approvedBy?: string | null;
  courseId?: string;
  lectureId?: string;
  lectureTitle?: string;
  revision?: string;
  reviewSeverity?: PracticeDesignReviewCheck["severity"] | null;
  sourceExcerpt?: string;
  sourcePath?: string;
  sourceRevision?: string;
  targetTitle?: string;
};

export function practiceDesignFixture(options: FixtureOptions = {}): PracticeDesign {
  const courseId = options.courseId ?? "course-1";
  const lectureId = options.lectureId ?? "lecture-03";
  const revision = options.revision ?? "d".repeat(64);
  const sourceRevision = options.sourceRevision ?? "s".repeat(64);
  const sourceAnchor = {
    source_path: options.sourcePath ?? "Lecture03.pdf",
    excerpt:
      options.sourceExcerpt ??
      "Choose the action with lower expected loss using the posterior probabilities.",
  };
  return {
    schema_version: 1,
    course_id: courseId,
    lecture_id: lectureId,
    lecture_title: options.lectureTitle ?? "Bayesian decision theory",
    objective: "Calculate a posterior from evidence.",
    planning_context: {
      learner_level: "Graduate seminar",
      prerequisites: ["Conditional probability"],
      time_budget_minutes: 45,
      allowed_aids: ["Formula sheet"],
      assessment_conditions: "Individual, unaided exit task",
      insufficiencies: [],
    },
    source_revision: sourceRevision,
    revision,
    quality_review:
      options.reviewSeverity === null
        ? null
        : qualityReviewFixture(
            sourceRevision,
            revision,
            options.reviewSeverity ?? "pass",
            sourceAnchor,
          ),
    approval: options.approvedBy
      ? {
          approved_at: "2026-08-26T12:00:00Z",
          approved_by: options.approvedBy,
          practice_design_revision: revision,
          source_revision: sourceRevision,
        }
      : null,
    targets: [
      {
        id: "posterior",
        title: options.targetTitle ?? "Posterior decisions",
        outcome: "Calculate a posterior from evidence.",
        outcome_anchor: sourceAnchor,
        target_invariant: "Apply the same posterior-weighted decision rule.",
        target_invariant_anchor: sourceAnchor,
        baseline_task: "Calculate the posterior.",
        baseline_task_anchor: sourceAnchor,
        independent_exit_task: "Calculate a new posterior.",
        independent_exit_task_anchor: sourceAnchor,
        independent_exit_surface_change: "Use new numerical values.",
        delayed_transfer_task: "Diagnose a posterior decision.",
        delayed_transfer_task_anchor: sourceAnchor,
        delayed_transfer_surface_change: "Use a changed clinical scenario.",
        evidence_criteria: [
          {
            id: "substitute",
            description: "Uses stated values.",
            required: true,
            source_anchor: sourceAnchor,
          },
        ],
        misconceptions: [
          {
            id: "prior",
            description: "Uses the prior only.",
            diagnostic_cue: "Prior.",
            source_anchor: sourceAnchor,
          },
        ],
        hint_ladder: [
          { level: "prompt", content: "Start with the evidence.", source_anchor: sourceAnchor },
        ],
        review_after_days: 7,
        source_refs: [sourceAnchor.source_path],
      },
    ],
  };
}

export function reviewedPracticeDesignFixture(design: PracticeDesign): PracticeDesign {
  return {
    ...design,
    quality_review: qualityReviewFixture(
      design.source_revision,
      design.revision,
      "pass",
      design.targets[0].outcome_anchor,
    ),
  };
}

function qualityReviewFixture(
  sourceRevision: string,
  revision: string,
  severity: PracticeDesignReviewCheck["severity"],
  sourceAnchor: PracticeDesign["targets"][number]["outcome_anchor"],
): PracticeDesignQualityReview {
  return {
    source_revision: sourceRevision,
    practice_design_revision: revision,
    checks: REVIEW_DIMENSIONS.map((dimension, index) => ({
      dimension,
      severity: index === 3 ? severity : "pass",
      summary:
        index === 3 && severity === "critical"
          ? "The exit task reveals the diagnostic answer."
          : "The design passes this check.",
      target_ids: index === 3 && severity !== "pass" ? ["posterior"] : [],
      supporting_anchors: index === 3 && severity !== "pass" ? [sourceAnchor] : [],
    })),
  };
}
