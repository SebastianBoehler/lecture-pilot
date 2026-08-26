export type PracticeEvidenceCriterion = Readonly<{
  id: string;
  description: string;
  required: boolean;
}>;

export type PracticeMisconception = Readonly<{
  id: string;
  description: string;
  diagnostic_cue: string;
}>;

export type PracticeHint = Readonly<{
  level: "prompt" | "cue" | "faded_example" | "worked_step";
  content: string;
}>;

export type PracticeTarget = Readonly<{
  id: string;
  title: string;
  outcome: string;
  baseline_task: string;
  independent_exit_task: string;
  delayed_transfer_task: string;
  evidence_criteria: readonly PracticeEvidenceCriterion[];
  misconceptions: readonly PracticeMisconception[];
  hint_ladder: readonly PracticeHint[];
  review_after_days: number;
  source_refs: readonly string[];
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
  source_revision: string;
  targets: readonly PracticeTarget[];
  revision: string;
  approval: PracticeDesignApproval | null;
}>;

export type PracticeDesignUpdate = Readonly<{
  source_revision: string;
  practice_design_revision: string;
  lecture_title: string;
  objective: string;
  targets: readonly PracticeTarget[];
}>;
