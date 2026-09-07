import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { I18nProvider } from "./i18n";
import { ProfessorPracticeDesignStep } from "./ProfessorPracticeDesignStep";
import { practiceDesignFixture } from "./practiceDesignTestFixtures";

it("blocks stale goal approval and offers a current-source proposal", async () => {
  const full = practiceDesignFixture({ approvedBy: null });
  const design = {
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
  const propose = vi.fn();
  render(
    <I18nProvider locale="en" setLocale={() => {}}>
      <ProfessorPracticeDesignStep
        designs={{ [design.lecture_id]: design }}
        readiness={{
          [design.lecture_id]: {
            lecture_id: design.lecture_id,
            current_source_revision: "b".repeat(64),
            practice_design_revision: design.revision,
            ready_for_generation: false,
          },
        }}
        lectures={[{ id: design.lecture_id, label: design.lecture_title }]}
        error={null}
        pendingAction={null}
        pendingLectureId={null}
        routingReady
        onApprove={vi.fn()}
        onSave={vi.fn()}
        onPropose={propose}
        onReview={vi.fn()}
      />
    </I18nProvider>,
  );
  expect(screen.getByRole("button", { name: "Approve learning goals" })).toBeDisabled();
  await userEvent.click(
    screen.getByRole("button", { name: "Regenerate goals for current sources" }),
  );
  expect(propose).toHaveBeenCalledWith(design.lecture_id, false);
});
