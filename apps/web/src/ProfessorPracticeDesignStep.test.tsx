import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { I18nProvider } from "./i18n";
import { ProfessorPracticeDesignStep } from "./ProfessorPracticeDesignStep";
import type { PracticeDesign, PracticeDesignUpdate } from "./practiceDesignTypes";

describe("ProfessorPracticeDesignStep", () => {
  it("presents an AI-authored review first and requires save before approval after a targeted edit", async () => {
    const user = userEvent.setup();
    const save = vi.fn();
    render(
      <I18nProvider locale="en" setLocale={() => undefined}>
        <ProfessorPracticeDesignStep
          designs={{ "lecture-03": design() }}
          error={null}
          lectures={[{ id: "lecture-03", label: "03 · Bayesian decision theory" }]}
          pendingLectureId={null}
          routingReady
          onApprove={vi.fn()}
          onPropose={vi.fn()}
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
          pendingLectureId={null}
          routingReady
          onApprove={vi.fn()}
          onPropose={propose}
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
              { id: "substitute", description: "Uses stated values.", required: false },
            ],
            misconceptions: [
              {
                id: "prior",
                description: "Uses the prior only.\nIgnores new evidence.",
                diagnostic_cue: "Prior repeated.\nLikelihood absent.",
              },
            ],
            hint_ladder: [
              {
                level: "worked_step",
                content: "Substitute the stated values step by step.",
              },
            ],
          }),
        ],
      }),
    );
  });

  it("supports an empty hint ladder and can start authoring one again", async () => {
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

    await user.click(screen.getByRole("button", { name: /add hint/i }));
    expect(screen.getByRole("combobox", { name: /hint level 1/i })).toHaveValue("prompt");
    expect(screen.getByLabelText(/hint content 1/i)).toHaveValue("");
  });
});

function renderStep(save: (lectureId: string, update: PracticeDesignUpdate) => void) {
  render(
    <I18nProvider locale="en" setLocale={() => undefined}>
      <ProfessorPracticeDesignStep
        designs={{ "lecture-03": design() }}
        error={null}
        lectures={[{ id: "lecture-03", label: "03 · Bayesian decision theory" }]}
        pendingLectureId={null}
        routingReady
        onApprove={vi.fn()}
        onPropose={vi.fn()}
        onSave={save}
      />
    </I18nProvider>,
  );
}

function design(approved = false): PracticeDesign {
  return {
    schema_version: 1,
    course_id: "course-1",
    lecture_id: "lecture-03",
    lecture_title: "Bayesian decision theory",
    objective: "Calculate a posterior from evidence.",
    source_revision: "s".repeat(64),
    revision: "d".repeat(64),
    approval: approved
      ? {
          approved_at: "2026-08-26T12:00:00Z",
          approved_by: "professor-demo",
          practice_design_revision: "d".repeat(64),
          source_revision: "s".repeat(64),
        }
      : null,
    targets: [
      {
        id: "posterior",
        title: "Posterior decisions",
        outcome: "Calculate a posterior from evidence.",
        baseline_task: "Calculate the posterior.",
        independent_exit_task: "Calculate a new posterior.",
        delayed_transfer_task: "Diagnose a posterior decision.",
        evidence_criteria: [
          { id: "substitute", description: "Uses stated values.", required: true },
        ],
        misconceptions: [
          { id: "prior", description: "Uses the prior only.", diagnostic_cue: "Prior." },
        ],
        hint_ladder: [{ level: "prompt", content: "Start with the evidence." }],
        review_after_days: 7,
        source_refs: ["Lecture03.pdf"],
      },
    ],
  };
}
