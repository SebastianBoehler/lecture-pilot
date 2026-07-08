import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import App from "./App";
import { openLecture03FromDashboard } from "./testLessonActions";
import {
  mockLoginAndTutorFetch,
  mockLoginFetch,
} from "./testFixtures";

describe("LecturePilot app shell", () => {
  it("starts with the university login form", () => {
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
    expect(screen.getByRole("navigation", { name: /student workspace navigation/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /workspaces/i })).toHaveClass("is-active");
    const probabilisticCourse = screen.getByRole("heading", {
      name: /probabilistic machine learning/i,
    }).closest("article");
    expect(probabilisticCourse).not.toBeNull();
    expect(within(probabilisticCourse as HTMLElement).getByText(/no tutor workspace yet/i)).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /grundlagen des maschinellen lernens/i })).not.toBeInTheDocument();
    expect(screen.queryByText(/matched from your alma course list/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /open lecture 03/i })).not.toBeInTheDocument();
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
    expect(window.sessionStorage.getItem("lecturepilot.loginSession")).toContain("signed-test-token");
    expect(window.localStorage.getItem("lecturepilot.loginSession")).not.toContain("signed-test-token");
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
    expect(screen.getByLabelText(/tutor model preference/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /workspaces/i }));
    expect(screen.getByRole("heading", { name: /course workspaces/i })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /open profile/i }));

    await user.click(screen.getByRole("button", { name: /log out/i }));

    expect(screen.getByRole("heading", { name: /sign in with uni tübingen/i })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /course workspaces/i })).not.toBeInTheDocument();
  });

  it("stores tutor model preference and sends it with tutor turns", async () => {
    const user = userEvent.setup();
    const fetchMock = mockLoginAndTutorFetch();
    vi.stubGlobal("fetch", fetchMock);
    renderPublishedApp();

    await logIn(user);
    await user.click(screen.getByRole("button", { name: /open profile/i }));
    await user.selectOptions(
      screen.getByLabelText(/tutor model preference/i),
      "openrouter/openai/gpt-oss-120b:nitro",
    );
    expect(window.localStorage.getItem("lecturepilot.tutorModelPreference"))
      .toBe("openrouter/openai/gpt-oss-120b:nitro");

    await user.click(screen.getByRole("button", { name: /dashboard/i }));
    await openLecture03FromDashboard(user);
    await user.click(screen.getByLabelText(/open tutor chat/i));
    await user.type(screen.getByPlaceholderText(/ask about this lecture/i), "Test fast model.");
    await user.click(screen.getByRole("button", { name: /send message/i }));

    await screen.findByText(/Bayes answer from the tutor/i);
    const agentCall = fetchMock.mock.calls.find(([url]) => String(url).includes("/agent/turn"));
    expect(agentCall?.[1]?.headers).toMatchObject({
      Authorization: "Bearer signed-test-token",
    });
    expect(JSON.parse(String(agentCall?.[1]?.body))).toMatchObject({
      model: "openrouter/openai/gpt-oss-120b:nitro",
    });
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
    expect(fetchMock.mock.calls.filter(([url]) => String(url).includes("/canvas/publication"))).toHaveLength(3);
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/canvas/publication"),
      expect.objectContaining({
        headers: expect.objectContaining({ "X-User-Id": "local-demo" }),
      }),
    );
  });

  it("opens plain-language project information from the footer", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: /how it works/i }));

    expect(screen.getByRole("heading", { name: /how lecturepilot works/i })).toBeInTheDocument();
    expect(screen.getByText(/think of each course as a small file system/i)).toBeInTheDocument();
    expect(screen.getByText(/the tutor uses attendance, quiz attempts, quality gates/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /datenschutz/i }));

    expect(screen.getByRole("heading", { name: /privacy notice/i })).toBeInTheDocument();
    expect(screen.getByText(/provider keys and model routing stay on the backend/i)).toBeInTheDocument();
  });

  it("opens a focused lesson workspace without showing the course dashboard", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", mockLoginFetch({ published: true }));
    renderPublishedApp();

    await logIn(user);
    await openLecture03FromDashboard(user);

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
    await openLecture03FromDashboard(user);
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
    await openLecture03FromDashboard(user);

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
    await openLecture03FromDashboard(user);

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
    await openLecture03FromDashboard(user);
    await user.click(screen.getByLabelText(/open tutor chat/i));
    expect(screen.getByText(/model after first turn/i)).toBeInTheDocument();

    const prompt = screen.getByPlaceholderText(/ask about this lecture/i);
    await user.type(prompt, "What are");
    await user.keyboard("{Shift>}{Enter}{/Shift}");
    await user.type(prompt, "the goals?");
    expect(prompt).toHaveValue("What are\nthe goals?");
    await user.keyboard("{Enter}");

    expect(await screen.findByText(/bayes answer/i)).toBeInTheDocument();
    expect(screen.getByText(/model: gemini\/gemini-3\.1-flash-lite/i)).toBeInTheDocument();
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

});

async function logIn(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText(/zdv username/i), "student01");
  await user.type(screen.getByLabelText(/^password$/i), "very-secret-password");
  await user.click(screen.getByRole("button", { name: /continue with uni tübingen/i }));
}

function renderPublishedApp() { render(<App />); }
