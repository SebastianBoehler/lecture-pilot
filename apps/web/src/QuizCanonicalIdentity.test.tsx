import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { I18nProvider } from "./i18n";
import { LessonWorkspace } from "./LessonWorkspace";
import type { LearnerLessonState } from "./learnerLessonStateTypes";
import type { CanvasDocument } from "./types";

describe("canonical quiz identity", () => {
  it("submits a component quiz with its canonical component id", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => quizResult,
    });
    vi.stubGlobal("fetch", fetchMock);
    renderWorkspace(null);

    await user.click(screen.getByRole("button", { name: /A Posterior only/i }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    const request = JSON.parse(String(fetchMock.mock.calls[0][1]?.body));
    expect(request.block_id).toBe("risk-component");
  });

  it("hydrates and locks a component quiz by its canonical id after reload", () => {
    renderWorkspace({
      course_id: "course-1",
      lecture_id: "lecture-1",
      gate_statuses: {},
      quiz_states: {
        "risk-component": {
          selected_index: 1,
          correct: true,
          publication_version: 1,
          attempt_index: 1,
          first_attempt_correct: true,
          latest_outcome: "correct",
          correction_state: "not_needed",
        },
      },
      active_session_goal: null,
      pending_check: null,
      due_gate_reviews: [],
    });

    expect(screen.getByRole("button", { name: /B Expected risk/i })).toBeDisabled();
    expect(screen.getByRole("status")).toHaveTextContent(/correct/i);
  });
});

function renderWorkspace(learnerState: LearnerLessonState | null) {
  return render(
    <I18nProvider locale="en" setLocale={vi.fn()}>
      <LessonWorkspace
        canvasDocument={canvas}
        canvasError={null}
        courseId="course-1"
        focusedSectionId="risk"
        highlightedBlockId={null}
        highlightedText={null}
        lecture={{
          id: "lecture-1",
          number: "01",
          title: "Risk",
          date: "2026-08-09",
          attendance: "present",
        }}
        learnerState={learnerState}
        learnerStateError={null}
        messages={[]}
        navigationVersion={0}
        panelMode={null}
        session={{ username: "student", term: "Summer 2026", courses: [] }}
        tutorModel={null}
        onPracticeSubmitted={vi.fn(async () => undefined)}
        onResetWorkspace={vi.fn(async () => undefined)}
        onSendMessage={vi.fn(async () => undefined)}
        onTogglePanel={vi.fn()}
      />
    </I18nProvider>,
  );
}

const canvas: CanvasDocument = {
  id: "course-1-lecture-1",
  course_id: "course-1",
  lecture_id: "lecture-1",
  title: "Risk",
  source_kind: "generated",
  source_ref: "test",
  sections: [
    {
      id: "risk",
      title: "Risk",
      blocks: [
        {
          id: "risk-component-shell",
          type: "component",
          component_id: "risk-component",
          component_type: "single_choice_quiz",
          text: "What should be minimized?",
          items: ["Posterior only", "Expected risk"],
        },
      ],
    },
  ],
};

const quizResult = {
  block_id: "risk-component",
  component_id: "risk-component",
  selected_index: 0,
  correct: false,
  publication_version: 1,
  attempt_index: 1,
  first_attempt_correct: false,
  latest_outcome: "incorrect",
  correction_state: "needed",
  feedback: "Review the explanation above, then try a correction.",
};
