import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

import { I18nProvider } from "./i18n";
import { ProfessorCanvasDraftStep } from "./ProfessorCanvasDraftStep";

it("summarizes historical generation failures until their details are requested", async () => {
  const user = userEvent.setup();
  render(
    <I18nProvider locale="en" setLocale={vi.fn()}>
      <ProfessorCanvasDraftStep
        canvas={null}
        canGenerate
        generatedCount={0}
        generationProgress={[
          {
            lectureId: "lecture-01",
            message: "The previous model response contained an unsupported claim.",
            status: "error",
          },
        ]}
        isFullCourse
        isGenerating={false}
        learningDesignAcknowledgementKey="professor:course-1:0"
        learningDesignReviews={{}}
        learningDesignSaving={false}
        previewLectures={[]}
        totalCount={1}
        onApproveLearningDesign={vi.fn()}
        onContinueToPublish={vi.fn()}
        onGenerate={vi.fn()}
        onRetry={vi.fn()}
        onSaveLearningDesign={vi.fn()}
      />
    </I18nProvider>,
  );

  expect(screen.getByText("Previous attempt failed")).toBeVisible();
  expect(screen.getByText(/results from the last generation run/i)).toBeVisible();
  const details = screen.getByText("View failure details").closest("details");
  expect(details).not.toHaveAttribute("open");

  await user.click(screen.getByText("View failure details"));
  expect(details).toHaveAttribute("open");
  expect(screen.getByText(/unsupported claim/i)).toBeVisible();
});
