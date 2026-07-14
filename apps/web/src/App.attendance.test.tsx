import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import {
  openLecture03FromDashboard,
  showAllPublishedLectures,
  soccerCanvasSection,
} from "./testLessonActions";
import { mockLoginAndTutorFetch, mockLoginFetch } from "./testFixtures";

describe("LecturePilot attendance tutor intro", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("seeds the tutor intro from the dashboard attendance choice", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", mockLoginFetch({ published: true }));
    render(<App />);

    await logIn(user);
    await showAllPublishedLectures(user);
    const lectureRow = (
      await screen.findByRole("heading", { name: /bayesian decision theory/i })
    ).closest("article");
    expect(lectureRow).not.toBeNull();
    await user.click(within(lectureRow as HTMLElement).getByRole("button", { name: "present" }));
    await openLecture03FromDashboard(user);
    await user.click(screen.getByLabelText(/open tutor chat/i));

    expect(screen.getByText(/you marked this lecture as attended/i)).toBeInTheDocument();
    expect(screen.getByText("mode: verification")).toBeInTheDocument();
    expect(screen.queryByText(/mark whether you attended/i)).not.toBeInTheDocument();
    expect(screen.queryByText("gate: needs evidence")).not.toBeInTheDocument();
  });

  it("uses attendance as tutor mode context and appends personalized canvas sections", async () => {
    const user = userEvent.setup();
    const fetchMock = mockLoginAndTutorFetch({
      tutorResponse: {
        message: "Guided walkthrough mode: I added a soccer example to the canvas.",
        canvas_commands: [
          {
            type: "append_section",
            section_id: "student-soccer-bayes-example",
            section: soccerCanvasSection(),
          },
          { type: "focus_section", section_id: "student-soccer-bayes-example" },
          {
            type: "highlight_span",
            section_id: "student-soccer-bayes-example",
            span_id: "student-soccer-bayes-example-p-1",
          },
        ],
        quality_gate: {
          gate_id: "bayes-decision-check",
          status: "needs_evidence",
          reason: "The student needs to map the example to Bayes terms.",
          next_prompt: "Name prior, likelihood, posterior, and risk in the soccer example.",
        },
        artifacts: [],
        model: "local-guided-preview",
        created_at: "2026-06-05T20:00:00Z",
      },
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    await logIn(user);
    await showAllPublishedLectures(user);
    const lectureRow = (
      await screen.findByRole("heading", { name: /bayesian decision theory/i })
    ).closest("article");
    expect(lectureRow).not.toBeNull();
    await user.click(within(lectureRow as HTMLElement).getByRole("button", { name: "absent" }));
    await openLecture03FromDashboard(user);
    await user.click(screen.getByLabelText(/open tutor chat/i));
    await user.type(
      screen.getByPlaceholderText(/ask about this lecture/i),
      "Explain this with a soccer example.",
    );
    await user.click(screen.getByRole("button", { name: /send message/i }));

    expect(
      await screen.findByRole("heading", { name: /soccer scouting example/i }),
    ).toBeInTheDocument();
    const history = screen.getByText("+1 earlier").closest("details");
    expect(history).not.toBeNull();
    expect(
      within(history as HTMLElement).getByText("canvas: student-soccer-bayes-example"),
    ).toBeInTheDocument();
    expect(screen.getByText("focus: student-soccer-bayes-example")).toBeInTheDocument();
    expect(screen.getByText("highlight: student-soccer-bayes-example-p-1")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: /soccer scouting example/i })).toHaveAttribute(
      "aria-current",
      "true",
    );

    const agentRequest = JSON.parse(String(fetchMock.mock.calls.at(-1)?.[1]?.body));
    expect(agentRequest).toMatchObject({
      attendance: "absent",
      canvas_state: { focused_section_id: "bayesian-decision-theory-the-aim" },
    });
    expect(agentRequest).not.toHaveProperty("user_id");
  });
});

async function logIn(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText(/zdv username/i), "student01");
  await user.type(screen.getByLabelText(/^password$/i), "very-secret-password");
  await user.click(screen.getByRole("button", { name: /continue with uni tübingen/i }));
}
