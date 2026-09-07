import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { I18nProvider } from "./i18n";
import { LessonWorkspace } from "./LessonWorkspace";
import type { TutorMessageOptions } from "./canvasLearningActions";
import type { CanvasDocument } from "./types";
import type { LearnerLessonState } from "./learnerLessonStateTypes";

describe("LessonWorkspace learning attempts", () => {
  it("keeps an unpublished professor draft free of learner requests and chat actions", () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "Student workspace access is required." }), {
        status: 403,
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    renderWorkspace({ onSendMessage: tutorMessageMock(), draftMode: true, panelMode: "chat" });
    expect(fetchMock).not.toHaveBeenCalled();
    expect(screen.queryByLabelText(/your checkpoint answer/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("textbox", { name: "Tutor message" })).not.toBeInTheDocument();
    expect(screen.getByText(/Unpublished draft/)).toBeInTheDocument();
    vi.unstubAllGlobals();
  });
  afterEach(() => {
    delete (Element.prototype as { scrollIntoView?: unknown }).scrollIntoView;
  });
  it("jumps to the section start and centers individual checks without unwanted motion", async () => {
    vi.stubGlobal(
      "matchMedia",
      vi.fn(() => ({ matches: true, addEventListener: vi.fn(), removeEventListener: vi.fn() })),
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
      screen.getByRole("button", { name: /Explain why expected loss changes/ }),
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
  it("closes teaching and chat until help is recorded and keeps them closed on failure", async () => {
    const state: LearnerLessonState = {
      course_id: "course-1",
      lecture_id: "lecture-1",
      publication_version: 1,
      gate_statuses: {},
      quiz_states: {},
      active_session_goal: "Apply expected loss",
      due_gate_reviews: [],
      pending_check: {
        gate_id: "risk-checkpoint",
        gate_revision: "revision",
        task_id: "independent-exit",
        issued_at: "2026-09-06T12:00:00Z",
        prompt: "Unaided new task",
        assistance_level: "none",
        kind: "standard",
        stage: "independent_exit",
        bank_exhausted: false,
        focus_required: true,
      },
    };
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce({ ok: false, json: async () => ({ detail: "Stale check" }) });
    vi.stubGlobal("fetch", fetcher);
    const view = renderWorkspace({ onSendMessage: tutorMessageMock(), learnerState: state });
    expect(screen.getByRole("region", { name: "Independent attempt" })).toBeInTheDocument();
    expect(screen.queryByText("What should be minimized?")).toBeNull();
    expect(screen.queryByRole("button", { name: /open chat/i })).toBeNull();
    await userEvent.type(screen.getByLabelText(/your checkpoint answer/i), "My partial reasoning");
    await userEvent.click(screen.getByRole("button", { name: "Request help and open materials" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Stale check");
    expect(screen.queryByText("What should be minimized?")).toBeNull();
    fetcher.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        ...state,
        pending_check: {
          ...state.pending_check,
          focus_required: false,
          stage: "exit_support",
          assistance_content: "Inspect the losses.",
        },
      }),
    });
    await userEvent.click(screen.getByRole("button", { name: "Request help and open materials" }));
    expect(screen.getByText("What should be minimized?")).toBeInTheDocument();
    expect(screen.getByText("Inspect the losses.")).toBeInTheDocument();
    expect(screen.getByLabelText(/your checkpoint answer/i)).toHaveValue("My partial reasoning");
    expect(JSON.parse(fetcher.mock.calls[1][1].body)).toMatchObject({
      task_id: "independent-exit",
      issued_at: state.pending_check!.issued_at,
    });
    view.setLearnerState({
      ...state,
      pending_check: {
        ...state.pending_check!,
        task_id: "exit-variant",
        issued_at: "2026-09-06T12:01:00Z",
        prompt: "Fresh task",
      },
    });
    expect(screen.getByText("Fresh task")).toBeInTheDocument();
    expect(screen.getByLabelText(/your checkpoint answer/i)).toHaveValue("");
    expect(screen.queryByText("What should be minimized?")).toBeNull();
    vi.unstubAllGlobals();
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
  draftMode = false,
}: {
  onSendMessage: (message: string, options?: TutorMessageOptions) => Promise<void>;
  learnerState?: LearnerLessonState | null;
  panelMode?: "outline" | "chat" | null;
  draftMode?: boolean;
}) {
  const view = (state: LearnerLessonState | null) => (
    <I18nProvider locale="en" setLocale={vi.fn()}>
      <LessonWorkspace
        draftMode={draftMode}
        canvasDocument={canvas}
        publishedCanvasView={
          draftMode
            ? null
            : {
                document: canvas,
                publication_version: 1,
                learning_map_revision: "revision",
              }
        }
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
        learnerState={
          state ?? {
            course_id: "course-1",
            lecture_id: "lecture-1",
            publication_version: 1,
            gate_statuses: {},
            quiz_states: {},
            active_session_goal: null,
            pending_check: null,
            due_gate_reviews: [],
          }
        }
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
