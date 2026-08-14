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

export type LearningDesignCoverage = {
  covered: number;
  total: number;
  status: "complete" | "incomplete" | "not_applicable";
};

export type LearningDesignDiagnostic = {
  id: string;
  code:
    | "assessment_section_source_missing"
    | "concept_without_assessment"
    | "inferred_linear_prerequisite"
    | "no_source_backed_assessment"
    | "quiz_only_no_open_checkpoint"
    | "worked_example_after_assessment";
  message: string;
  action: string;
  coordinates: {
    section_id: string | null;
    assessment_id: string | null;
    block_id: string | null;
    prerequisite_section_id: string | null;
  };
};

export type LearningDesignReport = {
  schema_version: 1;
  draft_digest: string;
  source_revision: string;
  learning_map_revision: string;
  report_revision: string;
  summary: {
    total_concepts: number;
    concepts_with_gate: number;
    concepts_with_quiz: number;
    concepts_with_assessment: number;
  };
  coverage: {
    gate_concepts: LearningDesignCoverage;
    quiz_concepts: LearningDesignCoverage;
    source_backed_assessments: LearningDesignCoverage;
    transfer_prompts: LearningDesignCoverage;
  };
  concepts: {
    section_id: string;
    title: string;
    gate_ids: string[];
    quiz_ids: string[];
    source_backed_assessment_ids: string[];
  }[];
  diagnostics: LearningDesignDiagnostic[];
};

export type LearningDesignReview = {
  schema_version: number;
  course_id: string;
  lecture_id: string;
  draft_digest: string;
  source_revision: string;
  factual_quality_separate: boolean;
  report: LearningDesignReport;
  approval: {
    approved_by: string;
    approved_at: string;
    draft_digest: string;
    source_revision: string;
    learning_map_revision: string;
    report_revision: string;
    acknowledged_warning_ids: string[];
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
> & {
  report_revision: string;
};
