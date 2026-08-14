import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { I18nProvider } from "./i18n";
import { ProfessorCanvasDraftStep } from "./ProfessorCanvasDraftStep";
import { learningDesignPayload } from "./testLearningDesignReviewFixture";

describe("ProfessorCanvasDraftStep review workspace", () => {
  it("opens each learner preview separately and reveals design review only on request", async () => {
    const user = userEvent.setup();
    const first = learningDesignPayload("course-1", "lecture-01", false);
    const second = learningDesignPayload("course-1", "lecture-02", true);
    second.learning_map.objective = "Transfer the translation mechanism.";

    render(
      <I18nProvider locale="en" setLocale={() => undefined}>
        <ProfessorCanvasDraftStep
          canvas={{ sections: [] } as never}
          canGenerate
          generatedCount={2}
          generationProgress={[
            { lectureId: "lecture-01", status: "ready" },
            { lectureId: "lecture-02", status: "ready" },
          ]}
          isFullCourse
          isGenerating={false}
          learningDesignReviews={{ "lecture-01": first, "lecture-02": second }}
          learningDesignSaving={false}
          previewLectures={[
            {
              id: "lecture-01",
              label: "01 · Introduction",
              previewHref: "http://localhost/draft/lecture-01",
            },
            {
              id: "lecture-02",
              label: "02 · Translation",
              previewHref: "http://localhost/draft/lecture-02",
            },
          ]}
          totalCount={2}
          onApproveLearningDesign={() => undefined}
          onContinueToPublish={() => undefined}
          onGenerate={() => undefined}
          onRetry={() => undefined}
          onSaveLearningDesign={() => undefined}
        />
      </I18nProvider>,
    );

    expect(screen.queryByTitle("Learner draft preview")).not.toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /open learner preview for 01 · introduction/i }),
    ).toHaveAttribute("href", "http://localhost/draft/lecture-01");
    expect(
      screen.getByRole("link", { name: /open learner preview for 02 · translation/i }),
    ).toHaveAttribute("target", "_blank");
    expect(screen.queryByLabelText("Learning objective")).not.toBeInTheDocument();

    await user.click(
      screen.getByRole("button", { name: /review learning design for 02 · translation/i }),
    );
    expect(screen.getByLabelText("Learning objective")).toHaveValue(
      "Transfer the translation mechanism.",
    );
  });
});
