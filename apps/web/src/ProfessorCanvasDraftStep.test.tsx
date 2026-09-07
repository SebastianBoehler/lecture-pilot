import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { I18nProvider } from "./i18n";
import { ProfessorCanvasDraftStep } from "./ProfessorCanvasDraftStep";
import {
  learningDesignDiagnosticFixture,
  learningDesignReportFixture,
} from "./testLearningDesignReportFixture";

describe("ProfessorCanvasDraftStep generation controls", () => {
  it("shows generation directly without a disclosure or duplicate notice", () => {
    renderStep({ isFullCourse: false, totalCount: 1 });
    const button = screen.getByRole("button", { name: "Generate draft canvas" });
    expect(button).toBeVisible();
    expect(button).toBeEnabled();
    expect(button.closest("details")).toBeNull();
    expect(screen.queryByLabelText("Generation timing")).not.toBeInTheDocument();
  });

  it("updates and disables the generation button while running", () => {
    renderStep({ isFullCourse: true, totalCount: 7, isGenerating: true });
    const button = screen.getByRole("button", { name: "Generating lecture canvases..." });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");
    expect(screen.getByRole("status")).toHaveClass("visually-hidden");
    expect(screen.getByRole("status")).toHaveTextContent(
      "Generating source-grounded canvases for 7 lectures...",
    );
  });

  it("keeps failed lectures retryable while other canvas work is running", () => {
    renderStep({
      generationProgress: [
        { lectureId: "lecture-05", status: "error" },
        { lectureId: "lecture-07", status: "error" },
      ],
      isFullCourse: true,
      isGenerating: true,
      totalCount: 14,
    });

    expect(screen.getByRole("button", { name: "Retry Lecture 05" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Retry Lecture 07" })).toBeEnabled();
  });

  it("disables only the lecture whose retry is being submitted", () => {
    renderStep({
      generationProgress: [
        { lectureId: "lecture-05", status: "error" },
        { lectureId: "lecture-07", status: "error" },
      ],
      isFullCourse: true,
      retryingLectureIds: new Set(["lecture-05"]),
      totalCount: 14,
    });

    expect(screen.getByRole("button", { name: "Retry Lecture 05" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Retry Lecture 07" })).toBeEnabled();
  });

  it("reviews the exact draft without an extra publishing step", () => {
    renderStep({
      isFullCourse: false,
      totalCount: 1,
      review: learningDesignReview(null),
    });

    openLearningDesign();
    expect(screen.getByRole("heading", { name: "Lecture canvas review" })).toBeInTheDocument();
    expect(screen.getByLabelText("Learning objective")).toHaveValue(
      "Explain the source-backed mechanism.",
    );
    expect(
      screen.getByText(/review the generated explanations and practice in the learner preview/i),
    ).toBeInTheDocument();
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
    expect(screen.queryByText("lecture.md#mechanism")).not.toBeInTheDocument();
    expect(screen.queryByText(/open-answer checkpoint coverage/i)).not.toBeInTheDocument();
    expect(screen.queryByText("Practice has no checkpoint or quiz.")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Continue to publishing" }),
    ).not.toBeInTheDocument();
  });

  it("edits and approves a per-lecture gate contract before continuing", () => {
    const onApproveLearningDesign = vi.fn();
    const onSaveLearningDesign = vi.fn();
    const { rerender } = renderStep({
      isFullCourse: false,
      totalCount: 1,
      onApproveLearningDesign,
      onSaveLearningDesign,
      review: learningDesignReview(null),
    });

    openLearningDesign();
    fireEvent.change(screen.getByLabelText("Learning objective"), {
      target: { value: "Explain and transfer the mechanism." },
    });
    fireEvent.click(screen.getByText("Edit practice details"));
    fireEvent.change(screen.getByLabelText("Review interval (days)"), {
      target: { value: "5" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save practice details" }));
    expect(onSaveLearningDesign).toHaveBeenCalledWith(
      "lecture-01",
      expect.objectContaining({
        objective: "Explain and transfer the mechanism.",
        gates: [expect.objectContaining({ id: "intro-check", review_after_days: 5 })],
      }),
    );
    const savedReview = learningDesignReview(null);
    savedReview.learning_map.objective = "Explain and transfer the mechanism.";
    savedReview.learning_map.gates[0].review_after_days = 5;
    rerender(
      step(savedReview, {
        onApproveLearningDesign,
        onSaveLearningDesign,
      }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Approve canvas for publication" }));
    expect(onApproveLearningDesign).toHaveBeenCalledWith("lecture-01");

    rerender(
      step(learningDesignReview("prof01"), {
        onApproveLearningDesign,
        onSaveLearningDesign,
      }),
    );
  });

  it("collapses a completed review and keeps the approved state when reopened", () => {
    const onApproveLearningDesign = vi.fn();
    const { rerender } = renderStep({
      isFullCourse: false,
      totalCount: 1,
      onApproveLearningDesign,
      review: learningDesignReview(null),
    });

    openLearningDesign();
    fireEvent.click(screen.getByRole("button", { name: "Approve canvas for publication" }));

    rerender(
      step(learningDesignReview("prof01"), {
        onApproveLearningDesign,
        onSaveLearningDesign: vi.fn(),
      }),
    );

    expect(
      screen.queryByRole("heading", { name: "Lecture canvas review" }),
    ).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /review lecture canvas for/i }));
    expect(screen.getByRole("button", { name: "Canvas approved for publication" })).toBeDisabled();
  });

  it("does not approve local edits until the exact changes are saved", () => {
    const onApproveLearningDesign = vi.fn();
    renderStep({
      isFullCourse: false,
      totalCount: 1,
      onApproveLearningDesign,
      review: learningDesignReview(null),
    });

    openLearningDesign();
    fireEvent.change(screen.getByLabelText("Learning objective"), {
      target: { value: "Unsaved changed objective." },
    });

    const approve = screen.getByRole("button", { name: "Approve canvas for publication" });
    expect(approve).toBeDisabled();
    expect(screen.getByText("Save these changes before approving this canvas.")).toHaveAttribute(
      "role",
      "status",
    );
    fireEvent.click(approve);
    expect(onApproveLearningDesign).not.toHaveBeenCalled();
  });
});

function openLearningDesign() {
  fireEvent.click(screen.getByRole("button", { name: /review lecture canvas for/i }));
}

function renderStep({
  isFullCourse,
  totalCount,
  onApproveLearningDesign = vi.fn(),
  onSaveLearningDesign = vi.fn(),
  review = null,
  generationProgress = [],
  isGenerating = false,
  retryingLectureIds = new Set(),
}: {
  isFullCourse: boolean;
  totalCount: number;
  onApproveLearningDesign?: (lectureId: string) => void;
  onSaveLearningDesign?: (lectureId: string, update: unknown) => void;
  review?: ReturnType<typeof learningDesignReview> | null;
  generationProgress?: Array<{
    lectureId: string;
    message?: string;
    status: "pending" | "generating" | "ready" | "error";
  }>;
  isGenerating?: boolean;
  retryingLectureIds?: ReadonlySet<string>;
}) {
  return render(
    step(
      review,
      { onApproveLearningDesign, onSaveLearningDesign },
      {
        generationProgress,
        isFullCourse,
        isGenerating,
        retryingLectureIds,
        totalCount,
      },
    ),
  );
}

function step(
  review: ReturnType<typeof learningDesignReview> | null,
  actions: {
    onApproveLearningDesign: (lectureId: string) => void;
    onSaveLearningDesign: (lectureId: string, update: unknown) => void;
  },
  overrides: {
    generationProgress?: Array<{
      lectureId: string;
      message?: string;
      status: "pending" | "generating" | "ready" | "error";
    }>;
    isFullCourse?: boolean;
    isGenerating?: boolean;
    retryingLectureIds?: ReadonlySet<string>;
    totalCount?: number;
  } = {},
) {
  return (
    <I18nProvider locale="en" setLocale={vi.fn()}>
      <ProfessorCanvasDraftStep
        canvas={review ? ({ sections: [] } as never) : null}
        canGenerate
        generatedCount={0}
        generationProgress={overrides.generationProgress ?? []}
        isFullCourse={overrides.isFullCourse ?? false}
        isGenerating={overrides.isGenerating ?? false}
        learningDesignReviews={review ? { "lecture-01": review } : {}}
        learningDesignSaving={false}
        onApproveLearningDesign={actions.onApproveLearningDesign}
        onGenerate={vi.fn()}
        onRetry={vi.fn()}
        retryingLectureIds={overrides.retryingLectureIds ?? new Set()}
        onSaveLearningDesign={actions.onSaveLearningDesign}
        previewLectures={
          review
            ? [
                {
                  id: "lecture-01",
                  label: "Lecture 01 · Mechanism",
                  previewHref: "http://localhost/draft/lecture-01",
                },
              ]
            : []
        }
        totalCount={overrides.totalCount ?? 1}
      />
    </I18nProvider>
  );
}

function learningDesignReview(approvedBy: string | null) {
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
          learning_map_revision: "m".repeat(64),
          report_revision: "r".repeat(64),
          acknowledged_warning_ids: [`concept_without_assessment:${"a".repeat(64)}`],
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
          review_after_days: 2,
          revision: "g".repeat(64),
          section_id: "intro",
          source_ref: "lecture.md#mechanism",
        },
      ],
    },
  };
}
