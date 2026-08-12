import { fireEvent, render, screen } from "@testing-library/react";
import type { ComponentType } from "react";
import { describe, expect, it } from "vitest";

import { I18nProvider } from "./i18n";
import { ProfessorLearningDesignReview } from "./ProfessorLearningDesignReview";

const ReviewComponent = ProfessorLearningDesignReview as ComponentType<Record<string, unknown>>;

describe("professor learning-design findings", () => {
  it("shows actionable findings without internal coverage or coordinates", () => {
    renderReview(reportReview());

    expect(screen.getByRole("heading", { name: "Review findings" })).toBeInTheDocument();
    expect(
      screen.getByText(/these automatic checks flag possible gaps; they do not change the draft/i),
    ).toBeInTheDocument();
    expect(screen.getByText("Practice has no checkpoint or quiz.")).toBeInTheDocument();
    expect(
      screen.getByText("Add a source-backed checkpoint or quiz to this section."),
    ).toBeInTheDocument();
    expect(
      screen.getAllByRole("checkbox", { name: "I reviewed this finding in the learner preview." }),
    ).toHaveLength(2);
    expect(screen.queryByText(/open-answer checkpoint coverage/i)).not.toBeInTheDocument();
    expect(
      screen.queryByText("Section practice · Assessment practice-quiz"),
    ).not.toBeInTheDocument();
  });

  it("blocks approval until every exact warning is acknowledged and sends canonical IDs", () => {
    let approval: { lectureId: string; warningIds: string[] } | null = null;
    renderReview(reportReview(), {
      onApprove: (lectureId: string, warningIds: string[]) => {
        approval = { lectureId, warningIds };
      },
    });
    const approve = screen.getByRole("button", { name: "Approve learning design" });
    const acknowledgements = screen.getAllByRole("checkbox");

    expect(approve).toBeDisabled();
    fireEvent.click(acknowledgements[0]);
    expect(approve).toBeDisabled();
    fireEvent.click(acknowledgements[1]);
    expect(approve).toBeEnabled();
    expect(screen.getByText("All findings reviewed for this exact draft.")).toBeInTheDocument();
    fireEvent.click(approve);

    expect(approval).toEqual({
      lectureId: "lecture-01",
      warningIds: [
        "concept_without_assessment:a".padEnd(91, "a"),
        "assessment_section_source_missing:b".padEnd(101, "b"),
      ],
    });
  });

  it("resets acknowledgements on save, report, identity, and stale-operation changes", () => {
    const initial = reportReview();
    const view = renderReview(initial, { acknowledgementResetKey: "identity-a:0" });
    acknowledgeAll();
    expect(screen.getByRole("button", { name: "Approve learning design" })).toBeEnabled();

    view.rerender(element(initial, { acknowledgementResetKey: "identity-a:1" }));
    expect(screen.getByRole("button", { name: "Approve learning design" })).toBeDisabled();
    acknowledgeAll();

    const revised = reportReview();
    revised.report.report_revision = "r".repeat(64);
    view.rerender(element(revised, { acknowledgementResetKey: "identity-a:1" }));
    expect(screen.getByRole("button", { name: "Approve learning design" })).toBeDisabled();
    acknowledgeAll();

    view.rerender(element(revised, { acknowledgementResetKey: "identity-b:0" }));
    expect(screen.getByRole("button", { name: "Approve learning design" })).toBeDisabled();
    acknowledgeAll();

    view.rerender(element(revised, { acknowledgementResetKey: "identity-b:stale" }));
    expect(screen.getByRole("button", { name: "Approve learning design" })).toBeDisabled();
  });
});

function acknowledgeAll() {
  for (const checkbox of screen.getAllByRole("checkbox")) fireEvent.click(checkbox);
}

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
