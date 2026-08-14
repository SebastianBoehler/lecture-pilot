import { fireEvent, render, screen } from "@testing-library/react";
import type { ComponentType } from "react";
import { describe, expect, it } from "vitest";

import { I18nProvider } from "./i18n";
import { ProfessorLearningDesignReview } from "./ProfessorLearningDesignReview";

const ReviewComponent = ProfessorLearningDesignReview as ComponentType<Record<string, unknown>>;

describe("professor learning-design approval", () => {
  it("keeps generator diagnostics out of the review and approves the exact design directly", () => {
    let approvedLectureId = "";
    renderReview(reportReview(), {
      onApprove: (lectureId: string) => (approvedLectureId = lectureId),
    });
    const approve = screen.getByRole("button", { name: "Approve learning design" });

    expect(screen.queryByRole("heading", { name: "Review findings" })).not.toBeInTheDocument();
    expect(screen.queryByText("Practice has no checkpoint or quiz.")).not.toBeInTheDocument();
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
    expect(approve).toBeEnabled();
    fireEvent.click(approve);
    expect(approvedLectureId).toBe("lecture-01");
  });
});

function renderReview(
  review: ReturnType<typeof reportReview>,
  overrides: Record<string, unknown> = {},
) {
  return render(element(review, overrides));
}

function element(review: ReturnType<typeof reportReview>, overrides: Record<string, unknown>) {
  return (
    <I18nProvider locale="en" setLocale={() => undefined}>
      <ReviewComponent
        acknowledgementResetKey="identity-a:0"
        lectureId="lecture-01"
        previewHref="http://localhost/draft/lecture-01"
        review={review}
        saving={false}
        onApprove={() => undefined}
        onSave={() => undefined}
        {...overrides}
      />
    </I18nProvider>
  );
}

function reportReview() {
  const firstId = "concept_without_assessment:a".padEnd(91, "a");
  const secondId = "assessment_section_source_missing:b".padEnd(101, "b");
  return {
    schema_version: 2,
    course_id: "course-1",
    lecture_id: "lecture-01",
    draft_digest: "d".repeat(64),
    source_revision: "s".repeat(64),
    factual_quality_separate: true,
    warnings: [],
    approval: null,
    learning_map: {
      course_id: "course-1",
      lecture_id: "lecture-01",
      title: "Mechanism",
      objective: "Explain the mechanism.",
      revision: "m".repeat(64),
      nodes: [
        {
          id: "practice",
          title: "Practice",
          lecture_id: "lecture-01",
          section_id: "practice",
          source_ref: null,
          prerequisites: [],
          gate_ids: [],
          quiz_ids: ["practice-quiz"],
        },
      ],
      gates: [],
    },
    report: {
      schema_version: 1,
      draft_digest: "d".repeat(64),
      source_revision: "s".repeat(64),
      learning_map_revision: "m".repeat(64),
      report_revision: "p".repeat(64),
      summary: {
        total_concepts: 2,
        concepts_with_gate: 1,
        concepts_with_quiz: 1,
        concepts_with_assessment: 1,
      },
      coverage: {
        gate_concepts: { covered: 1, total: 2, status: "incomplete" },
        quiz_concepts: { covered: 1, total: 2, status: "incomplete" },
        source_backed_assessments: { covered: 1, total: 2, status: "incomplete" },
        transfer_prompts: { covered: 1, total: 1, status: "complete" },
      },
      concepts: [],
      diagnostics: [
        {
          id: firstId,
          code: "concept_without_assessment",
          message: "Practice has no checkpoint or quiz.",
          action: "Add a source-backed checkpoint or quiz to this section.",
          coordinates: {
            section_id: "practice",
            assessment_id: "practice-quiz",
            block_id: null,
            prerequisite_section_id: null,
          },
        },
        {
          id: secondId,
          code: "assessment_section_source_missing",
          message: "The assessment has no local section source.",
          action: "Add a section-level source reference.",
          coordinates: {
            section_id: "practice",
            assessment_id: "practice-quiz",
            block_id: null,
            prerequisite_section_id: null,
          },
        },
      ],
    },
  };
}
