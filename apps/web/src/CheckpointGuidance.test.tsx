import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";
import { CheckpointGuidance, CheckpointGuidanceContext } from "./CheckpointGuidance";
import type { LearnerLessonState } from "./learnerLessonStateTypes";

it("shows guidance only at its own supported checkpoint and hides the hint until opened", async () => {
  const state: LearnerLessonState = {
    course_id: "course",
    lecture_id: "lecture",
    publication_version: 1,
    active_session_goal: null,
    gate_statuses: {},
    quiz_states: {},
    due_gate_reviews: [],
    pending_check: {
      gate_id: "check",
      gate_revision: "revision",
      prompt: "Explain.",
      assistance_level: "cue",
      kind: "standard",
      focus_required: false,
      bank_exhausted: true,
      assistance_content: "Look for **labels**.",
    },
  };
  const view = render(
    <CheckpointGuidanceContext.Provider value={state}>
      <CheckpointGuidance gateId="other" />
      <CheckpointGuidance gateId="check" />
    </CheckpointGuidanceContext.Provider>,
  );
  expect(screen.getAllByRole("status")).toHaveLength(1);
  expect(screen.getByText("labels")).not.toBeVisible();
  await userEvent.click(screen.getByText("Hint for this task"));
  expect(screen.getByText("labels")).toBeVisible();
  view.rerender(
    <CheckpointGuidanceContext.Provider
      value={{ ...state, pending_check: { ...state.pending_check!, focus_required: true } }}
    >
      <CheckpointGuidance gateId="check" />
    </CheckpointGuidanceContext.Provider>,
  );
  expect(screen.queryByRole("status")).not.toBeInTheDocument();
  expect(screen.queryByText("labels")).not.toBeInTheDocument();
});
