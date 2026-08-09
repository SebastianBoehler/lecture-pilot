import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { I18nProvider } from "./i18n";
import { LessonWorkspace } from "./LessonWorkspace";
import type { LearnerLessonState } from "./learnerLessonStateTypes";
import type { CanvasDocument } from "./types";

describe("canonical quiz identity", () => {
  it("hydrates and locks a component quiz by its canonical id after reload", () => {
    renderWorkspace({
      course_id: "course-1",
      lecture_id: "lecture-1",
      publication_version: 1,
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
        publishedCanvasView={{
          document: canvas,
          publication_version: 1,
          learning_map_revision: "a".repeat(64),
        }}
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
