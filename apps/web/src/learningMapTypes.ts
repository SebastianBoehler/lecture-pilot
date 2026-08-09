export type LearningMapGate = {
  id: string;
  concept_id: string;
  title: string;
  prompt: string;
  evidence_criteria: Array<{ id: string; description: string; required: boolean }>;
  transfer_prompt: string;
  review_after_days: number;
  revision: string;
  section_id: string;
  source_ref?: string | null;
};

export type LearningMapNode = {
  id: string;
  title: string;
  lecture_id: string;
  section_id: string;
  source_ref?: string | null;
  prerequisites: string[];
  gate_ids: string[];
  quiz_ids: string[];
};

export type LearningMap = {
  course_id: string;
  lecture_id: string;
  title: string;
  objective: string;
  revision: string;
  nodes: LearningMapNode[];
  gates: LearningMapGate[];
};
