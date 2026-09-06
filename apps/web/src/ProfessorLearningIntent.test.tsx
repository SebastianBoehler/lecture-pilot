import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { I18nProvider } from "./i18n";
import { ProfessorPracticeDesignStep } from "./ProfessorPracticeDesignStep";
import type { PracticeDesign } from "./practiceDesignTypes";
import { practiceDesignFixture } from "./practiceDesignTestFixtures";

function goalsOnly(): PracticeDesign {
  const full = practiceDesignFixture({ approvedBy: null });
  return {
    ...full,
    schema_version: 2,
    targets: [],
    quality_review: null,
    learning_intent: {
      source_revision: full.source_revision,
      objective: full.objective,
      planning_context: full.planning_context,
      revision: "i".repeat(64),
      approval: null,
      fixed_targets: [],
      goals: full.targets.map((target) => ({
        id: target.id,
        title: target.title,
        outcome: target.outcome,
        outcome_anchor: target.outcome_anchor,
        target_invariant: target.target_invariant,
        target_invariant_anchor: target.target_invariant_anchor,
      })),
    },
  };
}

function show(design: PracticeDesign, onApprove = vi.fn(), onSave = vi.fn()) {
  render(
    <I18nProvider locale="en" setLocale={() => {}}>
      <ProfessorPracticeDesignStep
        designs={{ [design.lecture_id]: design }}
        lectures={[{ id: design.lecture_id, label: design.lecture_title }]}
        error={null}
        pendingAction={null}
        pendingLectureId={null}
        routingReady
        onApprove={onApprove}
        onSave={onSave}
        onPropose={vi.fn()}
        onReview={vi.fn()}
      />
    </I18nProvider>,
  );
}

describe("professor learning intent", () => {
  it("approves source-backed goals before generated tasks or semantic task review exist", async () => {
    const design = goalsOnly();
    const approve = vi.fn();
    show(design, approve);
    expect(
      within(screen.getByRole("list")).getByText(design.learning_intent!.goals[0].outcome),
    ).toBeVisible();
    expect(screen.queryByText(/inspect generated practice/i)).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Approve learning goals" }));
    expect(approve).toHaveBeenCalledWith(design.lecture_id, {
      fixed_target_ids: [],
      convert_legacy: false,
    });
  });

  it("saves an edited goal and disables approval until its new revision is saved", async () => {
    const design = goalsOnly();
    const save = vi.fn();
    show(design, vi.fn(), save);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Edit learning goals" }));
    const outcome = screen.getByRole("textbox", { name: /outcome for/i });
    await user.clear(outcome);
    await user.type(outcome, "Justify the decision under changed source-supported conditions.");
    expect(screen.getByRole("button", { name: "Approve learning goals" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: /save learning plan/i }));
    expect(save.mock.calls[0][1].goals[0].outcome).toMatch(/^Justify the decision/);
    expect(save.mock.calls[0][1].targets).toEqual([]);
  });

  it("requires explicit consent before converting an existing full approval", async () => {
    const design = practiceDesignFixture({ approvedBy: "professor" });
    const approve = vi.fn();
    show(design, approve);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Review learning goals instead" }));
    const button = screen.getByRole("button", { name: "Approve learning goals" });
    expect(button).toBeDisabled();
    expect(screen.getByText(/existing approval is retained in history/i)).toBeVisible();
    await user.click(
      screen.getByRole("checkbox", { name: "I approve this change in responsibility" }),
    );
    await user.click(button);
    expect(approve).toHaveBeenCalledWith(design.lecture_id, {
      fixed_target_ids: [],
      convert_legacy: true,
    });
  });
});
