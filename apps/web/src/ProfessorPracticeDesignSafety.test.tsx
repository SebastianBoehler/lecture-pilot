import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

import { I18nProvider } from "./i18n";
import { ProfessorPracticeDesignStep } from "./ProfessorPracticeDesignStep";
import { practiceDesignFixture } from "./practiceDesignTestFixtures";
import type { PracticeDesign } from "./practiceDesignTypes";

it("keeps an ungrounded optional criterion optional", async () => {
  const user = userEvent.setup();
  const current = practiceDesignFixture();
  const target = current.targets[0];
  const ungrounded: PracticeDesign = {
    ...current,
    targets: [
      {
        ...target,
        evidence_criteria: target.evidence_criteria.map((criterion) => ({
          ...criterion,
          required: false,
          source_anchor: null,
        })),
      },
    ],
  };
  renderStep(ungrounded, null, null);

  await user.click(screen.getByRole("button", { name: /edit this target/i }));
  await user.selectOptions(
    screen.getByRole("combobox", { name: /choose what to edit/i }),
    "evidence",
  );
  expect(
    screen.getByRole("checkbox", { name: /criterion substitute is required/i }),
  ).toBeDisabled();
  expect(screen.getByText(/cannot be required without an exact source excerpt/i)).toBeVisible();
});

it("changes only the label for the active async action", () => {
  renderStep(practiceDesignFixture({ reviewSeverity: null }), "review", "lecture-03");

  expect(screen.getByRole("button", { name: /reviewing edited plan/i })).toBeDisabled();
  expect(screen.getByRole("button", { name: /^approve learning plan$/i })).toBeDisabled();
  expect(screen.getByText(/reviewing edited plan/i, { selector: "p" })).toBeVisible();
});

function renderStep(
  design: PracticeDesign,
  pendingAction: "review" | null,
  pendingLectureId: string | null,
) {
  render(
    <I18nProvider locale="en" setLocale={() => undefined}>
      <ProfessorPracticeDesignStep
        designs={{ "lecture-03": design }}
        error={null}
        lectures={[{ id: "lecture-03", label: "03 · Bayesian decision theory" }]}
        pendingAction={pendingAction}
        pendingLectureId={pendingLectureId}
        routingReady
        onApprove={vi.fn()}
        onPropose={vi.fn()}
        onReview={vi.fn()}
        onSave={vi.fn()}
      />
    </I18nProvider>,
  );
}
