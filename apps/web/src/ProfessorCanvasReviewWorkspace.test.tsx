import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { I18nProvider } from "./i18n";
import { ProfessorCanvasDraftStep } from "./ProfessorCanvasDraftStep";
import { learningDesignPayload } from "./testLearningDesignReviewFixture";

describe("ProfessorCanvasDraftStep review workspace", () => {
  it("reviews one lecture at a time without embedding every learner workspace", async () => {
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
          learningDesignAcknowledgementKey="professor:course-1:0"
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

    expect(screen.getAllByTitle("Learner draft preview")).toHaveLength(1);
    expect(screen.getByRole("button", { name: "01 · Introduction" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByTitle("Learner draft preview")).toHaveAttribute(
      "src",
      "http://localhost/draft/lecture-01",
    );

    await user.click(screen.getByRole("button", { name: "02 · Translation" }));
    expect(screen.getByTitle("Learner draft preview")).toHaveAttribute(
      "src",
      "http://localhost/draft/lecture-02",
    );

    await user.click(screen.getByRole("button", { name: "Review learning design" }));
    expect(screen.queryByTitle("Learner draft preview")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Learning objective")).toHaveValue(
      "Transfer the translation mechanism.",
    );
  });
});
