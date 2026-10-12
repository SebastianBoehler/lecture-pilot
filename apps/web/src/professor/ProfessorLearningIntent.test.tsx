import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { I18nProvider } from "../i18n/i18n";
import { ProfessorPracticeDesignStep } from "./ProfessorPracticeDesignStep";
import type { PracticeDesign } from "./practiceDesignTypes";
import { practiceDesignFixture } from "./practiceDesignTestFixtures";

function goalsOnly(): PracticeDesign {
  return { ...practiceDesignFixture({ approvedBy: null }), targets: [], quality_review: null };
}

function show(design: PracticeDesign, onApprove = vi.fn(), onSave = vi.fn(), onPropose = vi.fn()) {
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
        onPropose={onPropose}
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
    expect(approve).toHaveBeenCalledWith(design.lecture_id, { fixed_target_ids: [] });
  });

  it("regenerates unapproved goals through a new goal proposal", async () => {
    const design = goalsOnly();
    const propose = vi.fn();
    show(design, vi.fn(), vi.fn(), propose);
    await userEvent.click(screen.getByRole("button", { name: "Propose new learning goals" }));
    expect(propose).toHaveBeenCalledWith(design.lecture_id, true);
  });

  it("offers no goal regeneration once goals are approved", () => {
    const pending = goalsOnly();
    const design = {
      ...pending,
      targets: practiceDesignFixture({ approvedBy: null }).targets,
      learning_intent: {
        ...pending.learning_intent!,
        approval: {
          approved_by: "professor",
          approved_at: "2026-08-26T12:00:00Z",
          intent_revision: pending.learning_intent!.revision,
        },
      },
    };
    show(design);
    expect(screen.getByText("Learning goals approved")).toBeVisible();
    expect(screen.queryByRole("button", { name: /propose new learning goals/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /repair generated practice/i })).toBeNull();
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

  it("lets the professor rename and remove proposed goals before saving", async () => {
    const initial = goalsOnly();
    const first = initial.learning_intent!.goals[0];
    const design = {
      ...initial,
      learning_intent: {
        ...initial.learning_intent!,
        goals: [first, { ...first, id: "second-goal", title: "Second goal" }],
      },
    };
    const save = vi.fn();
    show(design, vi.fn(), save);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Edit learning goals" }));
    const title = screen.getByRole("textbox", { name: `Learning goal title: ${first.title}` });
    await user.clear(title);
    await user.type(title, "Updated learning goal");
    await user.click(screen.getByRole("button", { name: "Delete learning goal: Second goal" }));
    expect(screen.getByRole("button", { name: "Approve learning goals" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: /save learning plan/i }));
    expect(save.mock.calls[0][1].goals).toEqual([{ ...first, title: "Updated learning goal" }]);
  });
});
