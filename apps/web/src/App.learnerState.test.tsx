import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import App from "./App";
import { openLecture03FromDashboard } from "./testLessonActions";
import { mockLoginAndTutorFetch, mockLoginFetch } from "./testFixtures";

describe("durable learner lesson state", () => {
  it("hydrates persisted gate, quiz, and goal state again after reload", async () => {
    const baseFetch = mockLoginFetch({ published: true });
    let stateReads = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        if (url.includes("/learner-state")) {
          stateReads += 1;
          return json(persistedState("lecture-03", "Apply Bayes risk to a new case."));
        }
        return baseFetch(url, init);
      }),
    );
    const user = userEvent.setup();
    const first = render(<App />);

    await logIn(user);
    await openLecture03FromDashboard(user);
    const goal = await screen.findByText("Apply Bayes risk to a new case.");
    expect(goal.closest(".message-list")).toBeNull();
    expect(document.querySelector(".message-list")).toHaveAttribute("aria-live", "polite");
    await user.click(screen.getByLabelText(/open learning path/i));
    const path = await screen.findByRole("complementary", { name: /learning path panel/i });
    expect(within(path).getByText("Passed")).toBeInTheDocument();
    expect(within(path).getByText("Correct")).toBeInTheDocument();

    first.unmount();
    render(<App />);

    expect(await screen.findByText("Apply Bayes risk to a new case.")).toBeInTheDocument();
    expect(stateReads).toBeGreaterThanOrEqual(2);
  });

  it("does not let a late prior-lecture response overwrite the selected lesson", async () => {
    const baseFetch = mockLoginFetch({ published: true });
    let resolveLectureThree: ((value: ReturnType<typeof json>) => void) | undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string, init?: RequestInit) => {
        if (url.includes("lecture-03/learner-state")) {
          return new Promise((resolve) => {
            resolveLectureThree = resolve;
          });
        }
        if (url.includes("lecture-02/learner-state")) {
          return Promise.resolve(json(persistedState("lecture-02", "Lecture two goal.")));
        }
        return baseFetch(url, init);
      }),
    );
    const user = userEvent.setup();
    render(<App />);

    await logIn(user);
    await openLecture03FromDashboard(user);
    await act(async () => {
      window.history.pushState({}, "", "/courses/martius-ml/lectures/lecture-02");
      window.dispatchEvent(new PopStateEvent("popstate"));
    });

    expect(await screen.findByText("Lecture two goal.")).toBeInTheDocument();
    await act(async () => {
      resolveLectureThree?.(json(persistedState("lecture-03", "Stale lecture three goal.")));
    });
    await waitFor(() => {
      expect(screen.queryByText("Stale lecture three goal.")).not.toBeInTheDocument();
      expect(screen.getByText("Lecture two goal.")).toBeInTheDocument();
    });
  });

  it("refreshes state after a successful tutor turn", async () => {
    const baseFetch = mockLoginAndTutorFetch({
      tutorResponse: {
        message: "Your evidence now passes.",
        session_goal: "Use expected risk without hints.",
        canvas_commands: [],
        quality_gate: {
          gate_id: "bayes-decision-check",
          status: "passed",
          reason: "Evidence complete.",
        },
        model: "test/model",
      },
    });
    let persisted = false;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        if (url.includes("/learner-state")) {
          return json(
            persisted
              ? persistedState("lecture-03", "Use expected risk without hints.")
              : emptyState("lecture-03"),
          );
        }
        if (url.includes("/agent/turn") && !url.includes("/learner-state")) persisted = true;
        return baseFetch(url, init);
      }),
    );
    const user = userEvent.setup();
    render(<App />);

    await logIn(user);
    await openLecture03FromDashboard(user);
    await user.type(screen.getByPlaceholderText(/ask about this lecture/i), "Here is my answer.");
    await user.click(screen.getByRole("button", { name: /send message/i }));

    expect(await screen.findByText("Use expected risk without hints.")).toBeInTheDocument();
  });

  it("keeps a successful tutor update when an older hydration request finishes later", async () => {
    const baseFetch = mockLoginAndTutorFetch({
      tutorResponse: {
        message: "Goal updated.",
        session_goal: "Use the repaired strategy independently.",
        canvas_commands: [],
        quality_gate: null,
        model: "test/model",
      },
    });
    let stateReads = 0;
    let resolveHydration: ((value: ReturnType<typeof json>) => void) | undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string, init?: RequestInit) => {
        if (url.includes("/learner-state")) {
          stateReads += 1;
          if (stateReads > 1) {
            return Promise.resolve(
              json(persistedState("lecture-03", "Use the repaired strategy independently.")),
            );
          }
          return new Promise((resolve) => {
            resolveHydration = resolve;
          });
        }
        return baseFetch(url, init);
      }),
    );
    const user = userEvent.setup();
    render(<App />);

    await logIn(user);
    await openLecture03FromDashboard(user);
    await user.type(screen.getByPlaceholderText(/ask about this lecture/i), "My repaired answer.");
    await user.click(screen.getByRole("button", { name: /send message/i }));
    expect(await screen.findByText("Use the repaired strategy independently.")).toBeInTheDocument();

    await act(async () => {
      resolveHydration?.(json(persistedState("lecture-03", "Older goal.")));
    });
    expect(screen.queryByText("Older goal.")).not.toBeInTheDocument();
    expect(screen.getByText("Use the repaired strategy independently.")).toBeInTheDocument();
  });

  it("updates quiz state after practice persistence succeeds", async () => {
    const baseFetch = mockLoginAndTutorFetch();
    let quizPersisted = false;
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string, init?: RequestInit) => {
        if (url.includes("/learner-state")) {
          const state = emptyState("lecture-03");
          if (quizPersisted) {
            state.quiz_states["losses-and-risks-quiz"] = {
              selected_index: 1,
              correct: true,
            };
          }
          return Promise.resolve(json(state));
        }
        if (url.includes("/analytics/quiz-answer")) {
          quizPersisted = true;
          return Promise.resolve(
            json({
              block_id: "losses-and-risks-quiz",
              component_id: "losses-and-risks-quiz",
              selected_index: 1,
              correct_index: 1,
              correct: true,
            }),
          );
        }
        if (url.includes("/agent/turn/stream")) return new Promise(() => undefined);
        return baseFetch(url, init);
      }),
    );
    const user = userEvent.setup();
    render(<App />);

    await logIn(user);
    await openLecture03FromDashboard(user);
    await user.click(screen.getByRole("button", { name: /B Expected risk/i }));
    await user.click(screen.getByLabelText(/open learning path/i));

    const path = await screen.findByRole("complementary", { name: /learning path panel/i });
    expect(await within(path).findByText("Correct")).toBeInTheDocument();
  });

  it("shows persisted quiz state without waiting for an older hydration request", async () => {
    const baseFetch = mockLoginAndTutorFetch();
    let stateReads = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string, init?: RequestInit) => {
        if (url.includes("/learner-state")) {
          stateReads += 1;
          return stateReads === 1
            ? new Promise(() => undefined)
            : Promise.resolve(json(persistedState("lecture-03", "Durable goal.")));
        }
        if (url.includes("/analytics/quiz-answer")) {
          return Promise.resolve(
            json({
              block_id: "losses-and-risks-quiz",
              component_id: "losses-and-risks-quiz",
              selected_index: 1,
              correct_index: 1,
              correct: true,
            }),
          );
        }
        if (url.includes("/agent/turn/stream")) return new Promise(() => undefined);
        return baseFetch(url, init);
      }),
    );
    const user = userEvent.setup();
    render(<App />);

    await logIn(user);
    await openLecture03FromDashboard(user);
    await user.click(screen.getByRole("button", { name: /B Expected risk/i }));
    await user.click(screen.getByLabelText(/open learning path/i));

    const path = await screen.findByRole("complementary", { name: /learning path panel/i });
    expect(await within(path).findByText("Correct")).toBeInTheDocument();
  });
});

function persistedState(lectureId: string, goal: string) {
  return {
    ...emptyState(lectureId),
    gate_statuses: { "bayes-decision-check": "passed" },
    quiz_states: {
      "losses-and-risks-quiz": { selected_index: 1, correct: true },
    },
    active_session_goal: goal,
  };
}

function emptyState(lectureId: string) {
  return {
    course_id: "martius-ml",
    lecture_id: lectureId,
    gate_statuses: {} as Record<string, "passed" | "needs_evidence" | "not_assessed">,
    quiz_states: {} as Record<string, { selected_index: number; correct: boolean | null }>,
    active_session_goal: null as string | null,
    pending_check: null,
    due_gate_reviews: [],
  };
}

function json(payload: unknown) {
  return { ok: true, json: async () => payload };
}

async function logIn(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText(/zdv username/i), "student01");
  await user.type(screen.getByLabelText(/^password$/i), "very-secret-password");
  await user.click(screen.getByRole("button", { name: /continue with uni tübingen/i }));
}
