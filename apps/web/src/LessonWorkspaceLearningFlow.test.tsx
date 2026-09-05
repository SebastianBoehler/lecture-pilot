import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { I18nProvider } from "./i18n";
import { LessonWorkspace } from "./LessonWorkspace";
import type { TutorMessageOptions } from "./canvasLearningActions";
import type { CanvasDocument } from "./types";
import type { LearnerLessonState } from "./learnerLessonStateTypes";

describe("LessonWorkspace learning attempts", () => {
  afterEach(() => {
    delete (Element.prototype as { scrollIntoView?: unknown }).scrollIntoView;
  });
  it("jumps to the section start and centers individual checks without unwanted motion", async () => {
    vi.stubGlobal(
      "matchMedia",
      vi.fn(() => ({ matches: true })),
    );
    const scroll = vi.fn();
    Object.defineProperty(Element.prototype, "scrollIntoView", {
      configurable: true,
      value: scroll,
    });
    renderWorkspace({ onSendMessage: tutorMessageMock(), panelMode: "outline" });

    await userEvent.click(screen.getByRole("button", { name: "Risk" }));
    expect(scroll).toHaveBeenLastCalledWith({ behavior: "instant", block: "start" });
    await userEvent.click(
      screen.getByRole("button", { name: "Explain why expected loss changes the" }),
    );
    expect(scroll).toHaveBeenLastCalledWith({ behavior: "instant", block: "center" });
  });
  it("resumes the persisted check in the canvas without changing the published task", async () => {
    const user = userEvent.setup();
    const onSendMessage = tutorMessageMock();
    const view = renderWorkspace({
      onSendMessage,
      learnerState: {
        course_id: "course-1",
        lecture_id: "lecture-1",
        publication_version: 1,
        gate_statuses: {},
        quiz_states: {},
        active_session_goal: null,
        due_gate_reviews: [],
        pending_check: {
          gate_id: "risk-checkpoint",
          gate_revision: "revision",
          prompt: "Unaided, apply the idea to a new case.",
          assistance_level: "none",
          kind: "standard",
        },
      },
    });
    expect(screen.getByText("Unaided, apply the idea to a new case.")).toBeInTheDocument();
    expect(screen.queryByText("Explain why expected loss changes the decision.")).toBeNull();
    await user.type(screen.getByLabelText(/your checkpoint answer/i), "My new-case answer.");
    await user.click(screen.getByRole("button", { name: /submit checkpoint answer/i }));
    expect(onSendMessage).toHaveBeenCalledWith("My new-case answer.", {
      focusedSectionId: "risk",
      checkpointGateId: "risk-checkpoint",
    });
    expect(canvas.sections[0].blocks[1].text).toBe(
      "Explain why expected loss changes the decision.",
    );
    view.setLearnerState(null);
    expect(screen.getByLabelText(/your checkpoint answer/i)).toHaveValue("");
  });
  it("submits a checkpoint through the tutor with its published section and gate", async () => {
    const user = userEvent.setup();
    const onSendMessage = tutorMessageMock();
    renderWorkspace({ onSendMessage });

    await user.type(screen.getByLabelText(/your checkpoint answer/i), "Use expected loss.");
    await user.click(screen.getByRole("button", { name: /submit checkpoint answer/i }));

    expect(onSendMessage).toHaveBeenCalledWith("Use expected loss.", {
      focusedSectionId: "risk",
      checkpointGateId: "risk-checkpoint",
    });
  });
});

function renderWorkspace({
  onSendMessage,
  learnerState = null,
  panelMode = null,
}: {
  onSendMessage: (message: string, options?: TutorMessageOptions) => Promise<void>;
  learnerState?: LearnerLessonState | null;
  panelMode?: "outline" | null;
}) {
  const view = (state: LearnerLessonState | null) => (
    <I18nProvider locale="en" setLocale={vi.fn()}>
      <LessonWorkspace
        canvasDocument={canvas}
        publishedCanvasView={{
          document: canvas,
          publication_version: 1,
          learning_map_revision: "revision",
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
        messages={[]}
        navigationVersion={0}
        panelMode={panelMode}
        learnerState={state}
        learnerStateError={null}
        session={{ username: "student", term: "Summer 2026", courses: [] }}
        tutorModel={null}
        onResetWorkspace={vi.fn(async () => undefined)}
        onPracticeSubmitted={vi.fn(async () => undefined)}
        onSendMessage={onSendMessage}
        onTogglePanel={vi.fn()}
      />
    </I18nProvider>
  );
  const rendered = render(view(learnerState));
  return { setLearnerState: (state: LearnerLessonState | null) => rendered.rerender(view(state)) };
}

function tutorMessageMock() {
  return vi.fn(async (_message: string, _options?: TutorMessageOptions) => undefined);
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
          id: "risk-quiz",
          type: "quiz",
          text: "What should be minimized?",
          items: ["Posterior only", "Expected risk"],
        },
        {
          id: "risk-checkpoint",
          type: "checkpoint",
          text: "Explain why expected loss changes the decision.",
          items: [],
        },
      ],
    },
  ],
};
