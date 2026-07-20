import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { I18nProvider } from "./i18n";
import { ProfessorCanvasDraftStep } from "./ProfessorCanvasDraftStep";

describe("ProfessorCanvasDraftStep generation timing", () => {
  it("sets expectations before a single-lecture generation starts", () => {
    renderStep({ isFullCourse: false, totalCount: 1 });

    const notice = screen.getByLabelText("Generation timing");
    expect(notice).toHaveTextContent("about 10–15 minutes");
    expect(notice).toHaveTextContent("continues on the server");
    expect(notice).toHaveTextContent("leave this page and come back later");
  });

  it("estimates full-course duration from three concurrent lectures", () => {
    renderStep({ isFullCourse: true, totalCount: 7 });

    expect(screen.getByLabelText("Generation timing")).toHaveTextContent(
      "about 30–45 minutes for 7 lectures (up to 3 at once)",
    );
  });
});

function renderStep({ isFullCourse, totalCount }: { isFullCourse: boolean; totalCount: number }) {
  render(
    <I18nProvider locale="en" setLocale={vi.fn()}>
      <ProfessorCanvasDraftStep
        canvas={null}
        canGenerate
        generatedCount={0}
        generationProgress={[]}
        isFullCourse={isFullCourse}
        isGenerating={false}
        onContinueToPublish={vi.fn()}
        onGenerate={vi.fn()}
        onRetry={vi.fn()}
        previewLectures={[]}
        totalCount={totalCount}
      />
    </I18nProvider>,
  );
}
