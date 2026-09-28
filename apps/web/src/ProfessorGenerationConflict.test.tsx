import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

import { I18nProvider } from "./i18n";
import { ProfessorGenerationRowDetails } from "./ProfessorGenerationRowDetails";

it("directs an approved-scope conflict to learning-goal review instead of retry", async () => {
  const retry = vi.fn();
  const review = vi.fn();
  render(
    <I18nProvider locale="en" setLocale={vi.fn()}>
      <ProfessorGenerationRowDetails
        progress={{
          lectureId: "lecture-01",
          status: "error",
          errorKind: "design",
          message: "Revise the plan",
        }}
        retrying={false}
        onRetry={retry}
        onReviewLearningGoals={review}
      />
    </I18nProvider>,
  );
  expect(screen.getByRole("alert")).toHaveTextContent(/needs revision/i);
  expect(screen.queryByRole("button", { name: /retry/i })).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Review learning goals" }));
  expect(review).toHaveBeenCalledOnce();
  expect(retry).not.toHaveBeenCalled();
});
