import { I18nProvider } from "./i18n";
import { renderWithI18n } from "./test/renderWithI18n";
import { screen } from "@testing-library/react";
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
  const view = renderWithI18n(
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
    <I18nProvider locale="en" setLocale={() => undefined}>
      <CheckpointGuidanceContext.Provider
        value={{ ...state, pending_check: { ...state.pending_check!, focus_required: true } }}
      >
        <CheckpointGuidance gateId="check" />
      </CheckpointGuidanceContext.Provider>
    </I18nProvider>,
  );
  expect(screen.queryByRole("status")).not.toBeInTheDocument();
  expect(screen.queryByText("labels")).not.toBeInTheDocument();
});

it("stops checkpoint submissions when approved support is exhausted", async () => {
  const { CheckpointBlock } = await import("./CanvasLearningBlocks");
  const { vi } = await import("vitest");
  const submit = vi.fn();
  const state = {
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
      assistance_level: "none",
      kind: "standard",
      focus_required: false,
      support_exhausted: true,
      bank_exhausted: true,
      assistance_content: null,
    },
  } as LearnerLessonState;
  renderWithI18n(
    <CheckpointGuidanceContext.Provider value={state}>
      <CheckpointBlock
        block={{ id: "check", type: "checkpoint", text: "Explain.", items: [] }}
        className=""
        highlightedText={null}
        sourceMarker={null}
        sectionId="section"
        onSubmitCheckpoint={submit}
      />
    </CheckpointGuidanceContext.Provider>,
  );
  expect(screen.getByRole("status")).toHaveTextContent("Approved support is exhausted");
  expect(screen.getByRole("textbox")).toBeDisabled();
  expect(screen.getByRole("button", { name: "Submit checkpoint answer" })).toBeDisabled();
  expect(submit).not.toHaveBeenCalled();
});
