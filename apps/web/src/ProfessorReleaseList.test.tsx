import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { I18nProvider } from "./i18n";
import { ProfessorCanvasReviewWorkspace } from "./ProfessorCanvasReviewWorkspace";
import { learningDesignPayload } from "./testLearningDesignReviewFixture";

it("keeps mixed generation, review and publication states in one lecture list", async () => {
  const user = userEvent.setup();
  const retry = vi.fn();
  render(
    <I18nProvider locale="en" setLocale={() => undefined}>
      <ProfessorCanvasReviewWorkspace
        lectures={[
          { id: "lecture-01", label: "01 · Failed lecture", previewHref: "/draft/1" },
          { id: "lecture-02", label: "02 · Review lecture", previewHref: "/draft/2" },
          { id: "lecture-03", label: "03 · Approved lecture", previewHref: "/draft/3" },
          {
            id: "lecture-04",
            label: "04 · Published lecture",
            previewHref: "/draft/4",
            published: true,
          },
        ]}
        generationProgress={[
          { lectureId: "lecture-01", status: "error", message: "Service interrupted" },
          { lectureId: "lecture-02", status: "ready" },
          { lectureId: "lecture-03", status: "ready" },
          { lectureId: "lecture-04", status: "ready" },
        ]}
        learningDesignReviews={{
          "lecture-02": learningDesignPayload("course-1", "lecture-02", false),
          "lecture-03": learningDesignPayload("course-1", "lecture-03", true),
          "lecture-04": learningDesignPayload("course-1", "lecture-04", true),
        }}
        learningDesignSaving={false}
        onApproveLearningDesign={vi.fn()}
        onSaveLearningDesign={vi.fn()}
        onRetry={retry}
        renderPublishedLecture={() => <div>Language controls</div>}
      />
    </I18nProvider>,
  );
  const rows = within(screen.getByRole("list")).getAllByRole("listitem");
  expect(rows).toHaveLength(4);
  for (const [index, state] of ["Failed", "Needs review", "Approved", "Published"].entries()) {
    expect(within(rows[index]).getByText(state)).toBeInTheDocument();
  }
  expect(within(rows[0]).queryByRole("link")).not.toBeInTheDocument();
  await user.click(within(rows[0]).getByRole("button", { name: "Retry Lecture 01" }));
  expect(retry).toHaveBeenCalledWith("lecture-01");
  expect(screen.queryByText("Language controls")).not.toBeInTheDocument();
  await user.click(within(rows[3]).getByRole("button", { name: /review lecture canvas/i }));
  expect(within(rows[3]).getByText("Language controls")).toBeInTheDocument();
  await user.click(within(rows[1]).getByRole("button", { name: /review lecture canvas/i }));
  expect(screen.queryByText("Language controls")).not.toBeInTheDocument();
  expect(screen.getAllByRole("heading", { name: "Lecture canvas review" })).toHaveLength(1);
});
