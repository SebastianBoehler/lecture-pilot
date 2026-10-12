import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { I18nProvider } from "./i18n";
import { ProfessorPracticeDesignStep } from "./ProfessorPracticeDesignStep";
import { practiceDesignFixture } from "./practiceDesignTestFixtures";
import type { PracticeDesign, PracticeDesignUpdate } from "./practiceDesignTypes";

describe("ProfessorPracticeDesignStep", () => {
  it("preserves a dirty lecture draft across unrelated rerenders and failed saves", async () => {
    const user = userEvent.setup();
    const save = vi.fn();
    const view = renderStep(save);
    await editOutcome(user, "Keep this local edit.");
    await user.click(screen.getByRole("button", { name: /save learning plan/i }));
    expect(save).toHaveBeenCalledOnce();

    view.rerender(step({ onSave: save, pendingAction: "save", pendingLectureId: "lecture-03" }));
    expect(screen.getByLabelText(/outcome for posterior decisions/i)).toHaveValue(
      "Keep this local edit.",
    );

    view.rerender(step({ error: "Practice design failed to save.", onSave: save }));

    expect(screen.getByLabelText(/outcome for posterior decisions/i)).toHaveValue(
      "Keep this local edit.",
    );
    expect(screen.getByRole("alert")).toHaveTextContent(/failed to save/i);
  });

  it("preserves one lecture's dirty draft when another lecture changes", async () => {
    const user = userEvent.setup();
    const first = design();
    const second = practiceDesignFixture({ lectureId: "lecture-04", lectureTitle: "Lecture 04" });
    const view = render(
      step({
        designs: { "lecture-03": first, "lecture-04": second },
        lectures: [
          { id: "lecture-03", label: "03 · Bayesian decision theory" },
          { id: "lecture-04", label: "04 · Decision surfaces" },
        ],
      }),
    );
    await editOutcome(user, "Keep the first lecture edit.");

    view.rerender(
      step({
        designs: {
          "lecture-03": { ...first },
          "lecture-04": { ...second, revision: "e".repeat(64), objective: "Changed remotely." },
        },
        lectures: [
          { id: "lecture-03", label: "03 · Bayesian decision theory" },
          { id: "lecture-04", label: "04 · Decision surfaces" },
        ],
      }),
    );

    expect(screen.getByLabelText(/outcome for posterior decisions/i)).toHaveValue(
      "Keep the first lecture edit.",
    );
  });

  it("preserves dirty edits and surfaces an accessible conflict when their base revision changes", async () => {
    const user = userEvent.setup();
    const original = design();
    const view = render(step({ designs: { "lecture-03": original } }));
    await editOutcome(user, "My unsaved outcome.");

    view.rerender(
      step({
        designs: {
          "lecture-03": {
            ...original,
            revision: "e".repeat(64),
            objective: "A newer server objective.",
          },
        },
      }),
    );

    expect(screen.getByText("My unsaved outcome.")).toBeVisible();
    expect(screen.getByText(/newer version.*edits are preserved/i)).toBeVisible();
    expect(screen.getByRole("button", { name: /save learning plan/i })).toBeDisabled();

    await user.click(screen.getByRole("button", { name: /use latest plan/i }));
    expect(screen.queryByText(/newer version.*edits are preserved/i)).not.toBeInTheDocument();
  });

  it("offers proposal generation for a missing lecture and explains stale conflicts", async () => {
    const propose = vi.fn();
    render(
      <I18nProvider locale="en" setLocale={() => undefined}>
        <ProfessorPracticeDesignStep
          designs={{}}
          error="The practice design or source revision changed. Reload it."
          lectures={[{ id: "lecture-03", label: "03 · Bayesian decision theory" }]}
          pendingAction={null}
          pendingLectureId={null}
          routingReady
          onApprove={vi.fn()}
          onPropose={propose}
          onSave={vi.fn()}
        />
      </I18nProvider>,
    );

    expect(screen.getByRole("alert")).toHaveTextContent(/revision changed/i);
    await userEvent.setup().click(screen.getByRole("button", { name: /propose learning goals/i }));
    expect(propose).toHaveBeenCalledWith("lecture-03", false);
  });

  it("does not present an approved plan after source routing becomes stale", () => {
    render(
      <I18nProvider locale="en" setLocale={() => undefined}>
        <ProfessorPracticeDesignStep
          designs={{ "lecture-03": design(true) }}
          error={null}
          lectures={[{ id: "lecture-03", label: "03 · Bayesian decision theory" }]}
          pendingAction={null}
          pendingLectureId={null}
          routingReady={false}
          onApprove={vi.fn()}
          onPropose={vi.fn()}
          onSave={vi.fn()}
        />
      </I18nProvider>,
    );

    expect(screen.getByRole("alert")).toHaveTextContent(
      /regenerate or reconfirm source routing, refresh the plan, then approve/i,
    );
    expect(screen.queryByText(/learning goals approved/i)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /approve learning goals/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /edit learning goals/i })).toBeDisabled();
  });
});

function renderStep(save: (lectureId: string, update: PracticeDesignUpdate) => void) {
  return render(step({ onSave: save }));
}

function step(overrides: Partial<React.ComponentProps<typeof ProfessorPracticeDesignStep>> = {}) {
  return (
    <I18nProvider locale="en" setLocale={() => undefined}>
      <ProfessorPracticeDesignStep
        designs={{ "lecture-03": design() }}
        error={null}
        lectures={[{ id: "lecture-03", label: "03 · Bayesian decision theory" }]}
        pendingAction={null}
        pendingLectureId={null}
        routingReady
        onApprove={vi.fn()}
        onPropose={vi.fn()}
        onSave={vi.fn()}
        {...overrides}
      />
    </I18nProvider>
  );
}

async function editOutcome(user: ReturnType<typeof userEvent.setup>, value: string) {
  await user.click(screen.getByRole("button", { name: /edit learning goals/i }));
  const outcome = screen.getByLabelText(/outcome for posterior decisions/i);
  await user.clear(outcome);
  await user.type(outcome, value);
}

function design(approved = false): PracticeDesign {
  return practiceDesignFixture({
    approvedBy: approved ? "professor-demo" : null,
  });
}
