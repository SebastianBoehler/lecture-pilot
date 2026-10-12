import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { I18nProvider } from "./i18n";
import { ProfessorPracticeDesignStep } from "./ProfessorPracticeDesignStep";
import { practiceDesignFixture } from "./practiceDesignTestFixtures";
import type { PracticeDesign } from "./practiceDesignTypes";

function intentDesign(lectureId: string): PracticeDesign {
  const full = practiceDesignFixture({ approvedBy: null, lectureId, lectureTitle: lectureId });
  return {
    ...full,
    learning_intent: {
      source_revision: full.source_revision,
      objective: full.objective,
      planning_context: full.planning_context,
      revision: "i".repeat(64),
      approval: null,
      fixed_targets: [],
      goals: full.targets,
    },
  };
}

it("approves every open current learning plan with one action", async () => {
  const designs = Object.fromEntries(
    ["lecture-01", "lecture-02", "lecture-03"].map((id) => [id, intentDesign(id)]),
  );
  const stale = designs["lecture-03"];
  const approve = vi.fn();
  render(
    <I18nProvider locale="en" setLocale={() => {}}>
      <ProfessorPracticeDesignStep
        designs={designs}
        readiness={{
          "lecture-03": {
            lecture_id: "lecture-03",
            current_source_revision: "b".repeat(64),
            practice_design_revision: stale.revision,
            ready_for_generation: false,
          },
        }}
        lectures={Object.keys(designs).map((id) => ({ id, label: id }))}
        error={null}
        pendingAction={null}
        pendingLectureId={null}
        routingReady
        onApprove={approve}
        onSave={vi.fn()}
        onPropose={vi.fn()}
        onReview={vi.fn()}
      />
    </I18nProvider>,
  );
  await userEvent.click(screen.getByRole("button", { name: "Approve all 2 open learning plans" }));
  expect(approve.mock.calls).toEqual([
    ["lecture-01", { fixed_target_ids: [], convert_legacy: false }],
    ["lecture-02", { fixed_target_ids: [], convert_legacy: false }],
  ]);
});

it("shows advisory source findings next to the affected learning goal", () => {
  const design = intentDesign("lecture-01");
  const goal = design.learning_intent!.goals[0];
  render(
    <I18nProvider locale="en" setLocale={() => {}}>
      <ProfessorPracticeDesignStep
        designs={{
          "lecture-01": {
            ...design,
            goal_findings: [{ goal_id: goal.id, reason: "The slides only name it." }],
          },
        }}
        lectures={[{ id: "lecture-01", label: "lecture-01" }]}
        error={null}
        pendingAction={null}
        pendingLectureId={null}
        routingReady
        onApprove={vi.fn()}
        onSave={vi.fn()}
        onPropose={vi.fn()}
        onReview={vi.fn()}
      />
    </I18nProvider>,
  );
  expect(screen.getByRole("note")).toHaveTextContent("The slides only name it.");
  expect(screen.getByRole("button", { name: "Approve learning goals" })).toBeEnabled();
});
