import { learningDesignReportFixture } from "./testLearningDesignReportFixture";

export function learningDesignPayload(courseId: string, lectureId: string, approved: boolean) {
  return {
    schema_version: 2,
    course_id: courseId,
    lecture_id: lectureId,
    draft_digest: "d".repeat(64),
    source_revision: "s".repeat(64),
    factual_quality_separate: true,
    report: learningDesignReportFixture({
      draftDigest: "d".repeat(64),
      sourceRevision: "s".repeat(64),
      learningMapRevision: "m".repeat(64),
    }),
    approval: approved
      ? {
          approved_by: "professor-demo",
          approved_at: "2026-08-09T12:00:00Z",
          draft_digest: "d".repeat(64),
          source_revision: "s".repeat(64),
          learning_map_revision: "m".repeat(64),
          report_revision: "r".repeat(64),
          acknowledged_warning_ids: [],
        }
      : null,
    learning_map: {
      course_id: courseId,
      lecture_id: lectureId,
      title: "Bayesian Decision Theory",
      objective: "Explain Bayesian decisions from source evidence.",
      revision: "m".repeat(64),
      nodes: [],
      gates: [],
    },
  };
}
