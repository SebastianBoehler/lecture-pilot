import { fireEvent, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { renderWithI18n } from "./test/renderWithI18n";
import { OutlineProgress } from "./OutlineProgress";
import { practiceStatus } from "./practiceStatus";
import type { LearnerLessonState } from "./learnerLessonStateTypes";

const state: LearnerLessonState = {
  course_id: "course",
  lecture_id: "lecture",
  publication_version: 1,
  active_session_goal: "Distinguish the learning paradigms.",
  gate_statuses: {},
  quiz_states: {},
  pending_check: {
    gate_id: "check",
    gate_revision: "rev",
    prompt: "Explain the distinction.",
    assistance_level: "cue",
    kind: "standard",
    stage: "exit_support",
  },
  goal_evidence: [
    {
      gate_id: "check",
      gate_revision: "rev",
      supported: true,
      independent: false,
      delayed: false,
      missing_evidence_ids: [],
    },
  ],
  due_gate_reviews: [],
};

it("distinguishes supported, independent and delayed evidence without claiming mastery", () => {
  expect(practiceStatus("checkpoint", "check", state)).toBe("outline.supported");
  const independent = {
    ...state,
    goal_evidence: [{ ...state.goal_evidence![0], independent: true }],
  };
  expect(practiceStatus("checkpoint", "check", independent)).toBe("outline.independent");
  expect(
    practiceStatus("checkpoint", "check", {
      ...independent,
      goal_evidence: [{ ...independent.goal_evidence[0], delayed: true }],
    }),
  ).toBe("outline.delayed");
  expect(practiceStatus("checkpoint", "check", null)).toBe("outline.kind.gate");
});

it("explains the attempt flow and returns to the current checkpoint", () => {
  const onJumpAnchor = vi.fn();
  renderWithI18n(<OutlineProgress state={state} onJumpAnchor={onJumpAnchor} />);
  expect(screen.getByText("Distinguish the learning paradigms.")).toBeVisible();
  fireEvent.click(screen.getByText("How practice works"));
  expect(screen.getByText(/read the sections in any order/i)).toBeVisible();
  expect(screen.getByText(/one check at a time/i)).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Continue current check" }));
  expect(onJumpAnchor).toHaveBeenCalledWith("check");
});
