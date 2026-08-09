export type LearningDesignEvidenceCriterion = {
  id: string;
  description: string;
  required: boolean;
};

export type LearningDesignGate = {
  id: string;
  concept_id: string;
  title: string;
  prompt: string;
  evidence_criteria: LearningDesignEvidenceCriterion[];
  transfer_prompt: string;
  review_after_days: number;
  revision: string;
  section_id: string;
  source_ref: string | null;
};

export type LearningDesignNode = {
  id: string;
  title: string;
  lecture_id: string;
  section_id: string;
  source_ref: string | null;
  prerequisites: string[];
  gate_ids: string[];
  quiz_ids: string[];
};

export type LearningDesignReview = {
  schema_version: number;
  course_id: string;
  lecture_id: string;
  draft_digest: string;
  source_revision: string;
  factual_quality_separate: boolean;
  warnings: string[];
  approval: {
    approved_by: string;
    approved_at: string;
    draft_digest: string;
    source_revision: string;
    learning_map_revision: string;
  } | null;
  learning_map: {
    course_id: string;
    lecture_id: string;
    title: string;
    objective: string;
    revision: string;
    nodes: LearningDesignNode[];
    gates: LearningDesignGate[];
  };
};

export type LearningDesignUpdate = {
  draft_digest: string;
  source_revision: string;
  learning_map_revision: string;
  objective: string;
  gates: Pick<
    LearningDesignGate,
    "id" | "prompt" | "evidence_criteria" | "transfer_prompt" | "review_after_days"
  >[];
  prerequisites: { section_id: string; prerequisite_ids: string[] }[];
};

export type LearningDesignApprovalInput = Pick<
  LearningDesignUpdate,
  "draft_digest" | "source_revision" | "learning_map_revision"
>;
