import {
  learningDesignDiagnosticFixture,
  learningDesignReportFixture,
} from "./testLearningDesignReportFixture";
import type { LearningDesignReview } from "./learningDesignTypes";

export function learningDesignPayload(courseId: string, lectureId: string, approved: boolean) {
  return {
    schema_version: 2,
    course_id: courseId,
    lecture_id: lectureId,
    draft_digest: "d".repeat(64),
    source_revision: "s".repeat(64),
    practice_design_revision: "a".repeat(64),
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
          practice_design_revision: "a".repeat(64),
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

export function learningDesignReview(approvedBy: string | null): LearningDesignReview {
  return {
    schema_version: 2,
    course_id: "course-1",
    lecture_id: "lecture-01",
    draft_digest: "d".repeat(64),
    source_revision: "s".repeat(64),
    practice_design_revision: "a".repeat(64),
    factual_quality_separate: true,
    report: learningDesignReportFixture({
      draftDigest: "d".repeat(64),
      sourceRevision: "s".repeat(64),
      learningMapRevision: "m".repeat(64),
      diagnostics: [
        learningDesignDiagnosticFixture({
          message: "Practice has no checkpoint or quiz.",
          sectionId: "practice",
        }),
      ],
    }),
    approval: approvedBy
      ? {
          approved_by: approvedBy,
          approved_at: "2026-08-09T12:00:00Z",
          draft_digest: "d".repeat(64),
          source_revision: "s".repeat(64),
          practice_design_revision: "a".repeat(64),
        }
      : null,
    learning_map: {
      course_id: "course-1",
      lecture_id: "lecture-01",
      title: "Mechanism",
      objective: "Explain the source-backed mechanism.",
      revision: "m".repeat(64),
      nodes: [
        {
          id: "intro",
          title: "Mechanism",
          lecture_id: "lecture-01",
          section_id: "intro",
          source_ref: "lecture.md#mechanism",
          prerequisites: [],
          gate_ids: ["intro-check"],
          quiz_ids: [],
        },
      ],
      gates: [
        {
          id: "intro-check",
          concept_id: "intro",
          title: "Mechanism check",
          prompt: "Explain the mechanism.",
          evidence_criteria: [
            { id: "mechanism", description: "Names the mechanism.", required: true },
          ],
          transfer_prompt: "Apply it elsewhere.",
          practice_target_id: "mechanism",
          review_after_days: 2,
          revision: "g".repeat(64),
          section_id: "intro",
          source_ref: "lecture.md#mechanism",
        },
      ],
    },
  };
}
