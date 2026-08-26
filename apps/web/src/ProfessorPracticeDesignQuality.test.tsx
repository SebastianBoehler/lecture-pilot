import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

import { I18nProvider } from "./i18n";
import { ProfessorPracticeDesignStep } from "./ProfessorPracticeDesignStep";
import { practiceDesignFixture } from "./practiceDesignTestFixtures";
import type { PracticeDesignReviewCheck } from "./practiceDesignTypes";

it("shows planning context, exact evidence, and critical critic blockers", async () => {
  const user = userEvent.setup();
  renderStep("critical", vi.fn());

  expect(screen.getByText(/graduate seminar/i)).toBeVisible();
  expect(screen.getByText(/same posterior-weighted decision rule/i)).toBeVisible();
  expect(screen.getByText(/new numerical values/i)).toBeVisible();
  expect(screen.getByText(/changed clinical scenario/i)).toBeVisible();
  expect(screen.getAllByText(/critical issue/i)[0]).toBeVisible();
  expect(screen.getByText(/exit task reveals the diagnostic answer/i)).toBeVisible();
  expect(screen.getByRole("button", { name: /approve learning plan/i })).toBeDisabled();
  expect(screen.getByText(/approval is blocked/i)).toBeVisible();

  await user.click(screen.getAllByText(/show supporting source/i)[0]);
  expect(screen.getAllByText("Lecture03.pdf", { selector: "code" }).length).toBeGreaterThan(0);
  expect(screen.getAllByText(/choose the action with lower expected loss/i)[0]).toBeVisible();
});

it("keeps warnings visible without taking authority away from the professor", () => {
  renderStep("warning", vi.fn());

  expect(screen.getAllByText(/^warning$/i)[0]).toBeVisible();
  expect(screen.getByRole("button", { name: /approve learning plan/i })).toBeEnabled();
});

it("requires an explicit agent re-review for a saved edited revision", async () => {
  const user = userEvent.setup();
  const review = vi.fn();
  renderStep(null, review);

  expect(screen.getAllByText(/review required/i)[0]).toBeVisible();
  expect(screen.getByRole("button", { name: /approve learning plan/i })).toBeDisabled();
  await user.click(screen.getByRole("button", { name: /review edited plan/i }));
  expect(review).toHaveBeenCalledWith("lecture-03");
});

it("stops presenting the saved review as current after a draft edit", async () => {
  const user = userEvent.setup();
  renderStep("pass", vi.fn());

  expect(screen.getByText(/all eight pedagogical and source checks passed/i)).toBeVisible();
  await user.click(screen.getByRole("button", { name: /edit this target/i }));
  const outcome = screen.getByLabelText(/outcome for posterior decisions/i);
  await user.type(outcome, " independently");

  expect(
    screen.queryByText(/all eight pedagogical and source checks passed/i),
  ).not.toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /changes need review/i })).toBeVisible();
  expect(screen.getByText(/save the changes, then request a new agent review/i)).toBeVisible();
});

function renderStep(
  reviewSeverity: PracticeDesignReviewCheck["severity"] | null,
  onReview: (lectureId: string) => void,
) {
  render(
    <I18nProvider locale="en" setLocale={() => undefined}>
      <ProfessorPracticeDesignStep
        designs={{ "lecture-03": practiceDesignFixture({ reviewSeverity }) }}
        error={null}
        lectures={[{ id: "lecture-03", label: "03 · Bayesian decision theory" }]}
        pendingAction={null}
        pendingLectureId={null}
        routingReady
        onApprove={vi.fn()}
        onPropose={vi.fn()}
        onReview={onReview}
        onSave={vi.fn()}
      />
    </I18nProvider>,
  );
}
