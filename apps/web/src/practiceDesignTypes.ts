export type PracticeSourceAnchor = Readonly<{
  source_path: string;
  excerpt: string;
}>;

export type PracticePlanningContextField =
  | "learner_level"
  | "prerequisites"
  | "time_budget_minutes"
  | "allowed_aids"
  | "assessment_conditions";

export type PracticePlanningInsufficiency = Readonly<{
  field: PracticePlanningContextField;
  description: string;
}>;

export type PracticePlanningContext = Readonly<{
  learner_level: string | null;
  prerequisites: readonly string[] | null;
  time_budget_minutes: number | null;
  allowed_aids: readonly string[] | null;
  assessment_conditions: string | null;
  insufficiencies: readonly PracticePlanningInsufficiency[];
}>;

export type PracticeEvidenceCriterion = Readonly<{
  id: string;
  description: string;
  required: boolean;
  source_anchor: PracticeSourceAnchor | null;
}>;

export type PracticeMisconception = Readonly<{
  id: string;
  description: string;
  diagnostic_cue: string;
  source_anchor: PracticeSourceAnchor;
}>;

export type PracticeHint = Readonly<{
  level: "prompt" | "cue" | "faded_example" | "worked_step";
  content: string;
  source_anchor: PracticeSourceAnchor;
}>;

export type PracticeTarget = Readonly<{
  id: string;
  title: string;
  outcome: string;
  outcome_anchor: PracticeSourceAnchor;
  target_invariant: string;
  target_invariant_anchor: PracticeSourceAnchor;
  baseline_task: string;
  baseline_task_anchor: PracticeSourceAnchor;
  independent_exit_task: string;
  independent_exit_task_anchor: PracticeSourceAnchor;
  independent_exit_surface_change: string;
  delayed_transfer_task: string;
  delayed_transfer_task_anchor: PracticeSourceAnchor;
  delayed_transfer_surface_change: string;
  evidence_criteria: readonly PracticeEvidenceCriterion[];
  misconceptions: readonly PracticeMisconception[];
  hint_ladder: readonly PracticeHint[];
  review_after_days: number;
  source_refs: readonly string[];
}>;

export type PracticeReviewDimension =
  | "source_entailment"
  | "objective_task_alignment"
  | "exit_equivalence"
  | "answer_leakage"
  | "difficulty_drift"
  | "transfer_invariant_novelty"
  | "rubric_sufficiency"
  | "target_source_coverage";

export type PracticeDesignReviewCheck = Readonly<{
  dimension: PracticeReviewDimension;
  severity: "pass" | "warning" | "critical";
  summary: string;
  target_ids: readonly string[];
  supporting_anchors: readonly PracticeSourceAnchor[];
}>;

export type PracticeDesignQualityReview = Readonly<{
  source_revision: string;
  practice_design_revision: string;
  checks: readonly PracticeDesignReviewCheck[];
}>;

export type PracticeDesignApproval = Readonly<{
  approved_by: string;
  approved_at: string;
  source_revision: string;
  practice_design_revision: string;
}>;

export type PracticeDesign = Readonly<{
  schema_version: 1;
  course_id: string;
  lecture_id: string;
  lecture_title: string;
  objective: string;
  planning_context: PracticePlanningContext;
  source_revision: string;
  targets: readonly PracticeTarget[];
  revision: string;
  quality_review: PracticeDesignQualityReview | null;
  approval: PracticeDesignApproval | null;
}>;

export type PracticeDesignUpdate = Readonly<{
  source_revision: string;
  practice_design_revision: string;
  lecture_title: string;
  objective: string;
  planning_context: PracticePlanningContext;
  targets: readonly PracticeTarget[];
}>;
