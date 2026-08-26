import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { I18nProvider } from "./i18n";
import { ProfessorPracticeDesignStep } from "./ProfessorPracticeDesignStep";
import type { PracticeDesign } from "./practiceDesignTypes";

describe("ProfessorPracticeDesignStep", () => {
  it("keeps target details collapsed and requires save before approval after an edit", async () => {
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

    expect(screen.getByRole("heading", { name: /learning plans/i })).toBeInTheDocument();
    expect(screen.getByText("Posterior decisions", { selector: "strong" })).toBeInTheDocument();
    const details = screen.getByText(/edit target details/i).closest("details");
    expect(details).not.toHaveAttribute("open");
    expect(screen.queryByLabelText(/target id/i)).not.toBeInTheDocument();

    await user.click(details!.querySelector("summary")!);
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
    expect(screen.getByLabelText(/lecture objective/i)).toBeDisabled();
  });
});

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
