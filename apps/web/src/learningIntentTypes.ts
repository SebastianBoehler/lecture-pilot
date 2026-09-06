import type { PracticePlanningContext, PracticeSourceAnchor } from "./practiceDesignTypes";

export type LearningIntent = Readonly<{
  source_revision: string;
  objective: string;
  planning_context: PracticePlanningContext;
  goals: readonly Readonly<{
    id: string;
    title: string;
    outcome: string;
    outcome_anchor: PracticeSourceAnchor;
    target_invariant: string;
    target_invariant_anchor: PracticeSourceAnchor;
  }>[];
  fixed_targets: readonly Readonly<{ id: string; revision: string }>[];
  revision: string;
  approval: Readonly<{ approved_by: string; approved_at: string; intent_revision: string }> | null;
}>;

export type LearningIntentApprovalOptions = {
  fixed_target_ids: readonly string[];
  convert_legacy: boolean;
};
