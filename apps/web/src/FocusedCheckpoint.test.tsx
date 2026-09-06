import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { FocusedCheckpoint } from "./LearningEvidenceFlow";
import { I18nProvider } from "./i18n";
import type { LearnerLessonState } from "./learnerLessonStateTypes";
import type { CanvasDocument } from "./types";

it("cannot request help while an independent answer is being assessed", async () => {
  let finish!: () => void;
  const onSubmit = vi.fn(
    () =>
      new Promise<void>((resolve) => {
        finish = resolve;
      }),
  );
  const onHelp = vi.fn(async () => undefined);
  const state: LearnerLessonState = {
    course_id: "course",
    lecture_id: "lecture",
    publication_version: 1,
    gate_statuses: {},
    quiz_states: {},
    active_session_goal: null,
    due_gate_reviews: [],
    pending_check: {
      gate_id: "gate",
      gate_revision: "revision",
      prompt: "New independent task",
      task_id: "fresh",
      issued_at: "now",
      stage: "independent_exit",
      assistance_level: "none",
      kind: "standard",
      focus_required: true,
    },
  };
  const document: CanvasDocument = {
    id: "doc",
    course_id: "course",
    lecture_id: "lecture",
    title: "Lesson",
    source_kind: "markdown",
    source_ref: "source",
    sections: [
      {
        id: "section",
        title: "Concept",
        blocks: [{ id: "gate", type: "checkpoint", text: "Diagnostic", items: [] }],
      },
    ],
  };
  render(
    <I18nProvider locale="en" setLocale={vi.fn()}>
      <FocusedCheckpoint
        state={state}
        document={document}
        onSubmit={onSubmit}
        onHelp={onHelp}
        busy={false}
        error={null}
      />
    </I18nProvider>,
  );
  await userEvent.type(screen.getByLabelText(/your checkpoint answer/i), "My reasoning");
  await userEvent.click(screen.getByRole("button", { name: /submit checkpoint answer/i }));
  expect(screen.getByRole("button", { name: "Request help and open materials" })).toBeDisabled();
  await userEvent.click(screen.getByRole("button", { name: "Request help and open materials" }));
  expect(onHelp).not.toHaveBeenCalled();
  await act(async () => finish());
  expect(screen.getByRole("button", { name: "Request help and open materials" })).toBeEnabled();
});
