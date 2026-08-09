import type { LearningDesignDiagnostic, LearningDesignReport } from "./learningDesignTypes";

export function learningDesignReportFixture({
  diagnostics = [],
  draftDigest,
  learningMapRevision,
  sourceRevision,
}: {
  diagnostics?: LearningDesignDiagnostic[];
  draftDigest: string;
  learningMapRevision: string;
  sourceRevision: string;
}): LearningDesignReport {
  return {
    schema_version: 1,
    draft_digest: draftDigest,
    source_revision: sourceRevision,
    learning_map_revision: learningMapRevision,
    report_revision: "r".repeat(64),
    summary: {
      total_concepts: 1,
      concepts_with_gate: 1,
      concepts_with_quiz: 0,
      concepts_with_assessment: 1,
    },
    coverage: {
      gate_concepts: { covered: 1, total: 1, status: "complete" },
      quiz_concepts: { covered: 0, total: 1, status: "incomplete" },
      source_backed_assessments: { covered: 1, total: 1, status: "complete" },
      transfer_prompts: { covered: 1, total: 1, status: "complete" },
    },
    concepts: [],
    diagnostics,
  };
}

export function learningDesignDiagnosticFixture({
  code = "concept_without_assessment",
  message,
  sectionId,
}: {
  code?: LearningDesignDiagnostic["code"];
  message: string;
  sectionId: string;
}): LearningDesignDiagnostic {
  return {
    id: `${code}:${"a".repeat(64)}`,
    code,
    message,
    action: "Add a source-backed checkpoint or quiz to this section.",
    coordinates: {
      section_id: sectionId,
      assessment_id: null,
      block_id: null,
      prerequisite_section_id: null,
    },
  };
}
