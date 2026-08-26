import { render, screen, within } from "@testing-library/react";
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

    expect(screen.getByLabelText(/outcome for posterior decisions/i)).toHaveValue(
      "My unsaved outcome.",
    );
    expect(screen.getByRole("status")).toHaveTextContent(/newer version.*edits are preserved/i);
    expect(screen.getByRole("button", { name: /save learning plan/i })).toBeDisabled();

    await user.click(screen.getByRole("button", { name: /use latest plan/i }));
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    expect(screen.getAllByText("A newer server objective.")[0]).toBeVisible();
  });

  it("presents an AI-authored review first and requires save before approval after a targeted edit", async () => {
    const user = userEvent.setup();
    const save = vi.fn();
    render(
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
          onReview={vi.fn()}
          onSave={save}
        />
      </I18nProvider>,
    );

    expect(screen.getByRole("heading", { name: /review learning plans/i })).toBeInTheDocument();
    expect(
      screen.getByText(/lecturepilot drafts each plan from confirmed sources/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/posterior decisions/i, { selector: "strong" })).toBeInTheDocument();
    expect(screen.queryByLabelText(/lecture title/i)).not.toBeInTheDocument();
    const sequence = screen.getByRole("list", { name: /practice sequence/i });
    expect(within(sequence).getByText(/reveals current reasoning before support/i)).toBeVisible();

    await user.click(screen.getByRole("button", { name: /edit this target/i }));
    const section = screen.getByRole("combobox", { name: /choose what to edit/i });
    expect(section).toHaveValue("outcome");
    expect(screen.queryByLabelText(/baseline task/i)).not.toBeInTheDocument();
    expect(screen.getByText("posterior", { selector: "code" })).toBeInTheDocument();
    const outcome = screen.getByLabelText(/outcome for posterior decisions/i);
    await user.clear(outcome);
    await user.type(outcome, "Calculate a calibrated posterior.");

    expect(screen.getByRole("button", { name: /approve learning plan/i })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: /save learning plan/i }));
    expect(save).toHaveBeenCalledWith(
      "lecture-03",
      expect.objectContaining({
        practice_design_revision: "d".repeat(64),
        targets: [
          expect.objectContaining({
            id: "posterior",
            outcome: "Calculate a calibrated posterior.",
          }),
        ],
      }),
    );
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
          onReview={vi.fn()}
          onSave={vi.fn()}
        />
      </I18nProvider>,
    );

    expect(screen.getByRole("alert")).toHaveTextContent(/revision changed/i);
    await userEvent.setup().click(screen.getByRole("button", { name: /generate learning plan/i }));
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
          onReview={vi.fn()}
          onSave={vi.fn()}
        />
      </I18nProvider>,
    );

    expect(screen.getByRole("alert")).toHaveTextContent(
      /regenerate or reconfirm source routing, refresh the plan, then approve/i,
    );
    expect(screen.getByText(/source routing is stale/i)).toBeInTheDocument();
    expect(screen.queryByText(/^approved$/i)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /approve learning plan/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /refresh proposal/i })).toBeDisabled();
    expect(screen.queryByRole("button", { name: /edit lecture details/i })).not.toBeInTheDocument();
  });

  it("round-trips every mutable contract field without multiplexing multiline values", async () => {
    const user = userEvent.setup();
    const save = vi.fn();
    renderStep(save);

    await user.click(screen.getByRole("button", { name: /edit lecture details/i }));
    const lectureTitle = screen.getByLabelText(/lecture title/i);
    await user.clear(lectureTitle);
    await user.type(lectureTitle, "Bayesian evidence decisions");
    await user.click(screen.getByRole("button", { name: /edit this target/i }));
    const section = screen.getByRole("combobox", { name: /choose what to edit/i });

    expect(screen.getByText("posterior", { selector: "code" })).toBeInTheDocument();
    await user.selectOptions(section, "evidence");
    const required = screen.getByRole("checkbox", { name: /criterion substitute is required/i });
    await user.click(required);

    await user.selectOptions(section, "misconceptions");
    const description = screen.getByLabelText(/misconception description.*prior/i);
    await user.clear(description);
    await user.type(description, "Uses the prior only.{enter}Ignores new evidence.");
    const diagnosticCue = screen.getByLabelText(/diagnostic cue.*prior/i);
    await user.clear(diagnosticCue);
    await user.type(diagnosticCue, "Prior repeated.{enter}Likelihood absent.");

    await user.selectOptions(section, "hints");
    const hintLevel = screen.getByLabelText(/hint level 1/i);
    expect(
      within(hintLevel)
        .getAllByRole("option")
        .map((option) => option.getAttribute("value")),
    ).toEqual(["prompt", "cue", "faded_example", "worked_step"]);
    await user.selectOptions(hintLevel, "worked_step");
    const hintContent = screen.getByLabelText(/hint content 1/i);
    await user.clear(hintContent);
    await user.type(hintContent, "Substitute the stated values step by step.");
    await user.click(screen.getByRole("button", { name: /save learning plan/i }));

    expect(save).toHaveBeenCalledWith(
      "lecture-03",
      expect.objectContaining({
        lecture_title: "Bayesian evidence decisions",
        targets: [
          expect.objectContaining({
            evidence_criteria: [
              expect.objectContaining({
                id: "substitute",
                description: "Uses stated values.",
                required: false,
              }),
            ],
            misconceptions: [
              expect.objectContaining({
                id: "prior",
                description: "Uses the prior only.\nIgnores new evidence.",
                diagnostic_cue: "Prior repeated.\nLikelihood absent.",
              }),
            ],
            hint_ladder: [
              expect.objectContaining({
                level: "worked_step",
                content: "Substitute the stated values step by step.",
              }),
            ],
          }),
        ],
      }),
    );
  });

  it("does not fabricate grounding when the professor removes all agent-authored hints", async () => {
    const user = userEvent.setup();
    const save = vi.fn();
    renderStep(save);
    await user.click(screen.getByRole("button", { name: /edit this target/i }));
    await user.selectOptions(
      screen.getByRole("combobox", { name: /choose what to edit/i }),
      "hints",
    );

    await user.click(screen.getByRole("button", { name: /remove hint 1/i }));
    expect(screen.queryByRole("combobox", { name: /hint level/i })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /save learning plan/i }));
    expect(save).toHaveBeenCalledWith(
      "lecture-03",
      expect.objectContaining({
        targets: [expect.objectContaining({ hint_ladder: [] })],
      }),
    );

    expect(screen.queryByRole("button", { name: /add hint/i })).not.toBeInTheDocument();
    expect(
      screen.getByText(/regenerate the proposal to add source-grounded scaffold content/i),
    ).toBeVisible();
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
        onReview={vi.fn()}
        onSave={vi.fn()}
        {...overrides}
      />
    </I18nProvider>
  );
}

async function editOutcome(user: ReturnType<typeof userEvent.setup>, value: string) {
  await user.click(screen.getByRole("button", { name: /edit this target/i }));
  const outcome = screen.getByLabelText(/outcome for posterior decisions/i);
  await user.clear(outcome);
  await user.type(outcome, value);
}

function design(approved = false): PracticeDesign {
  return practiceDesignFixture({
    approvedBy: approved ? "professor-demo" : null,
  });
}
