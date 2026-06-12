import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import App from "./App";
import { mockLoginAndTutorFetch, mockLoginFetch, soccerCanvasSection } from "./testFixtures";

describe("LecturePilot app shell", () => {
  it("starts with a TUE API wrapper login form", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: /sign in with uni tübingen/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/zdv username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/term/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /course workspaces/i })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^lecturepilot$/i })).toBeInTheDocument();
    expect(screen.queryByText(/^course workspace$/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/openrouter glm/i)).not.toBeInTheDocument();
  });

  it("logs in through the local backend and shows authenticated courses", async () => {
    const user = userEvent.setup();
    const fetchMock = mockLoginFetch();
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    await logIn(user);

    expect(await screen.findByRole("heading", { name: /welcome, student01@uni-tuebingen\.de/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /course workspaces/i })).toBeInTheDocument();
    const probabilisticCourse = screen.getByRole("heading", {
      name: /probabilistic machine learning/i,
    }).closest("article");
    const martiusCourse = screen.getByRole("heading", {
      name: /grundlagen des maschinellen lernens/i,
    }).closest("article");
    expect(probabilisticCourse).not.toBeNull();
    expect(martiusCourse).not.toBeNull();
    expect(within(probabilisticCourse as HTMLElement).getByText(/no tutor workspace yet/i)).toBeInTheDocument();
    expect(within(martiusCourse as HTMLElement).getByText(/no tutor workspace yet/i)).toBeInTheDocument();
    expect(screen.queryByText(/matched from your alma course list/i)).not.toBeInTheDocument();
    expect(within(martiusCourse as HTMLElement).queryByRole("button", { name: /open lecture 03/i })).not.toBeInTheDocument();
    expect(screen.queryByText("very-secret-password")).not.toBeInTheDocument();
    const request = JSON.parse(String(fetchMock.mock.calls[0][1]?.body));
    expect(request).toEqual({
      username: "student01",
      password: "very-secret-password",
    });
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/auth/login"),
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("opens the profile view and logs out", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", mockLoginFetch({ published: true }));
    render(<App />);

    await logIn(user);
    await user.click(screen.getByRole("button", { name: /open profile/i }));

    expect(screen.getByRole("heading", { name: /profile/i })).toBeInTheDocument();
    expect(screen.getByText("student01")).toBeInTheDocument();
    expect(screen.getByText(/student01@uni-tuebingen\.de/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /log out/i }));

    expect(screen.getByRole("heading", { name: /sign in with uni tübingen/i })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /course workspaces/i })).not.toBeInTheDocument();
  });

  it("opens a local demo workspace without submitting credentials", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    await user.click(screen.getByRole("button", { name: /preview local demo/i }));

    expect(screen.getByRole("heading", { name: /welcome, local-demo/i, level: 1 })).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: /grundlagen des maschinellen lernens/i, level: 1 }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /course workspaces/i })).toBeInTheDocument();
    expect(screen.getByText(/no tutor workspace yet/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /open lecture 03/i })).not.toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/canvas/publication"),
      expect.objectContaining({
        headers: expect.objectContaining({ "X-User-Id": "local-demo" }),
      }),
    );
  });

  it("opens a focused lesson workspace without showing the course dashboard", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", mockLoginFetch({ published: true }));
    renderPublishedApp();

    await logIn(user);
    await user.click(await screen.findByRole("button", { name: /open lecture 03/i }));

    expect(
      screen.getByRole("heading", { name: /^bayesian decision theory$/i, level: 1 }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /course workspaces/i })).not.toBeInTheDocument();
    expect(screen.getByLabelText(/open tutor chat/i)).toBeInTheDocument();
    expect(screen.queryByPlaceholderText(/ask about this lecture/i)).not.toBeInTheDocument();
  });

  it("switches the focused workspace rail between tutor, outline, and notes", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", mockLoginFetch({ published: true }));
    renderPublishedApp();

    await logIn(user);
    await user.click(await screen.findByRole("button", { name: /open lecture 03/i }));
    await user.click(screen.getByLabelText(/open tutor chat/i));

    expect(screen.getByPlaceholderText(/ask about this lecture/i)).toBeInTheDocument();

    await user.click(screen.getByLabelText(/open document outline/i));

    expect(screen.getByRole("heading", { name: /document outline/i })).toBeInTheDocument();
    const outline = screen.getByRole("navigation", { name: /lesson document outline/i });
    expect(
      within(outline).getByRole("button", { name: /bayes formula and conditional probability/i }),
    ).toBeInTheDocument();
    expect(within(outline).getByRole("button", { name: /ch3\/spam-dall-e.jpg/i })).toBeInTheDocument();
    expect(within(outline).queryByRole("button", { name: /^formula$/i })).not.toBeInTheDocument();
    expect(
      within(outline).getByRole("group", { name: /decision making under uncertainty related items/i }),
    ).toBeInTheDocument();
    expect(screen.queryByPlaceholderText(/ask about this lecture/i)).not.toBeInTheDocument();

    await user.click(screen.getByLabelText(/open lecture notes panel/i));

    const notesPanel = screen.getByRole("complementary", { name: /lecture notes panel/i });
    expect(within(notesPanel).getByRole("heading", { name: /source notes/i })).toBeInTheDocument();
    expect(within(notesPanel).getByText(/official latex source/i)).toBeInTheDocument();
    expect(within(notesPanel).getByText(/lecture03-eng\.tex/i)).toBeInTheDocument();
  });

  it("renders professor course canvas blocks instead of old demo artifacts", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", mockLoginFetch({ published: true }));
    renderPublishedApp();

    await logIn(user);
    await user.click(await screen.findByRole("button", { name: /open lecture 03/i }));

    expect(screen.queryByRole("heading", { name: /course source packet/i })).not.toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /bayes formula and conditional probability/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /ch3\/spam-dall-e.jpg/i })).toBeInTheDocument();
    expect(document.querySelector(".canvas-math .katex")).not.toBeNull();
    expect(document.querySelectorAll(".katex").length).toBeGreaterThan(1);
    expect(screen.getAllByText(/lecture03-eng\.tex/i).length).toBeGreaterThan(0);

    await user.click(screen.getByLabelText(/open document outline/i));
    const outline = screen.getByRole("navigation", { name: /lesson document outline/i });

    expect(within(outline).queryByRole("button", { name: /course source packet/i })).not.toBeInTheDocument();

    await user.click(
      within(outline).getByRole("button", { name: /bayes formula and conditional probability/i }),
    );

    expect(screen.getByRole("region", { name: /bayes formula and conditional probability/i })).toHaveAttribute(
      "aria-current",
      "true",
    );
  });

  it("renders imported lecture sections in the lesson canvas", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", mockLoginFetch({ published: true }));
    renderPublishedApp();

    await logIn(user);
    await user.click(await screen.findByRole("button", { name: /open lecture 03/i }));

    expect(screen.getByRole("region", { name: /bayes rule for classification/i })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: /naive bayes spam filter/i })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: /losses, risks, and reject decisions/i })).toBeInTheDocument();
  });

  it("toggles dark mode with a document theme attribute", async () => {
    const user = userEvent.setup();
    renderPublishedApp();

    await user.click(screen.getByRole("button", { name: /switch to dark mode/i }));

    expect(document.documentElement.dataset.theme).toBe("dark");
  });

  it("sends a tutor message and applies canvas focus commands", async () => {
    const user = userEvent.setup();
    const fetchMock = mockLoginAndTutorFetch();
    vi.stubGlobal("fetch", fetchMock);
    renderPublishedApp();

    await user.click(screen.getByRole("button", { name: /preview local demo/i }));
    await user.click(await screen.findByRole("button", { name: /open lecture 03/i }));
    await user.click(screen.getByLabelText(/open tutor chat/i));
    expect(screen.getByText(/model after first turn/i)).toBeInTheDocument();

    const prompt = screen.getByPlaceholderText(/ask about this lecture/i);
    await user.type(prompt, "What are");
    await user.keyboard("{Shift>}{Enter}{/Shift}");
    await user.type(prompt, "the goals?");
    expect(prompt).toHaveValue("What are\nthe goals?");
    await user.keyboard("{Enter}");

    expect(await screen.findByText(/bayes answer/i)).toBeInTheDocument();
    expect(screen.getByText(/model: gemini\/gemini-2\.5-flash-lite/i)).toBeInTheDocument();
    expect(screen.getByText("focus: bayes-formula")).toBeInTheDocument();
    expect(screen.getAllByText("gate: needs evidence").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByRole("region", { name: /bayes formula and conditional probability/i })).toHaveAttribute(
      "aria-current",
      "true",
    );
    const agentRequest = JSON.parse(String(fetchMock.mock.calls.at(-1)?.[1]?.body));
    expect(agentRequest.user_id).toBe("local-demo");
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/agent/turn"),
      expect.objectContaining({ method: "POST" }),
    );
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
    renderPublishedApp();

    await logIn(user);
    const lectureRow = (await screen.findByRole("heading", { name: /bayesian decision theory/i })).closest("article");
    expect(lectureRow).not.toBeNull();
    await user.click(within(lectureRow as HTMLElement).getByRole("button", { name: "absent" }));
    await user.click(await screen.findByRole("button", { name: /open lecture 03/i }));
    await user.click(screen.getByLabelText(/open tutor chat/i));
    await user.type(
      screen.getByPlaceholderText(/ask about this lecture/i),
      "Explain this with a soccer example.",
    );
    await user.click(screen.getByRole("button", { name: /send message/i }));

    expect(await screen.findByRole("heading", { name: /soccer scouting example/i })).toBeInTheDocument();
    expect(screen.queryByText("canvas: student-soccer-bayes-example")).not.toBeInTheDocument();
    expect(screen.getByText("+1 earlier")).toBeInTheDocument();
    expect(screen.getByText("focus: student-soccer-bayes-example")).toBeInTheDocument();
    expect(screen.getByText("highlight: student-soccer-bayes-example-p-1")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: /soccer scouting example/i })).toHaveAttribute(
      "aria-current",
      "true",
    );

    const agentRequest = JSON.parse(String(fetchMock.mock.calls.at(-1)?.[1]?.body));
    expect(agentRequest).toMatchObject({
      user_id: "student01",
      attendance: "absent",
      canvas_state: { focused_section_id: "bayesian-decision-theory-the-aim" },
    });
  });
});

async function logIn(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText(/zdv username/i), "student01");
  await user.type(screen.getByLabelText(/^password$/i), "very-secret-password");
  await user.click(screen.getByRole("button", { name: /connect to tue api/i }));
}

function renderPublishedApp() { render(<App />); }
