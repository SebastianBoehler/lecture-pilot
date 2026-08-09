import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { I18nProvider } from "./i18n";
import { LessonWorkspace } from "./LessonWorkspace";
import type { TutorMessageOptions } from "./canvasLearningActions";
import type { CanvasDocument } from "./types";

describe("LessonWorkspace learning attempts", () => {
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

  it("shows a quiz API error instead of sending an unaccepted answer to chat", async () => {
    const user = userEvent.setup();
    const onSendMessage = tutorMessageMock();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        json: async () => ({ detail: "Quiz attempt could not be stored." }),
      }),
    );
    renderWorkspace({ onSendMessage });

    await user.click(screen.getByRole("button", { name: "A Posterior only" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Quiz attempt could not be stored.");
    expect(onSendMessage).not.toHaveBeenCalled();
  });

  it("sends one attempt id and tutor message only after quiz persistence succeeds", async () => {
    const user = userEvent.setup();
    const onSendMessage = tutorMessageMock();
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        block_id: "risk-quiz",
        component_id: "risk-quiz",
        selected_index: 0,
        correct: false,
        publication_version: 1,
        attempt_index: 1,
        first_attempt_correct: false,
        latest_outcome: "incorrect",
        correction_state: "needed",
        feedback: "Review the explanation above, then try a correction.",
      }),
    });
    vi.stubGlobal("fetch", fetchMock);
    renderWorkspace({ onSendMessage });

    await user.click(screen.getByRole("button", { name: "A Posterior only" }));

    await waitFor(() => expect(onSendMessage).toHaveBeenCalledTimes(1));
    const request = JSON.parse(String(fetchMock.mock.calls[0][1]?.body));
    expect(request.attempt_id).toEqual(expect.any(String));
    expect(onSendMessage).toHaveBeenCalledWith(expect.stringContaining("Posterior only"));
  });
});

function renderWorkspace({
  onSendMessage,
}: {
  onSendMessage: (message: string, options?: TutorMessageOptions) => Promise<void>;
}) {
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
        messages={[]}
        navigationVersion={0}
        panelMode={null}
        learnerState={null}
        learnerStateError={null}
        session={{ username: "student", term: "Summer 2026", courses: [] }}
        tutorModel={null}
        onResetWorkspace={vi.fn(async () => undefined)}
        onPracticeSubmitted={vi.fn(async () => undefined)}
        onSendMessage={onSendMessage}
        onTogglePanel={vi.fn()}
      />
    </I18nProvider>,
  );
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
