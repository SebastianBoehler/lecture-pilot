import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import App from "./App";
import { openLecture03FromDashboard } from "./testLessonActions";
import { mockLoginAndTutorFetch, mockLoginFetch } from "./testFixtures";

describe("LecturePilot app shell", () => {
  it("starts with the university login form", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: /welcome to lecturepilot/i })).toBeInTheDocument();
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

    expect(
      await screen.findByRole("heading", { name: /welcome, student example/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /course workspaces/i })).toBeInTheDocument();
    expect(
      screen.getByRole("navigation", { name: /student workspace navigation/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /workspaces/i })).toHaveClass("is-active");
    const probabilisticCourse = screen
      .getByRole("heading", {
        name: /probabilistic machine learning/i,
      })
      .closest("article");
    expect(probabilisticCourse).not.toBeNull();
    expect(
      within(probabilisticCourse as HTMLElement).getByText(/not supported yet/i),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: /grundlagen des maschinellen lernens/i }),
    ).not.toBeInTheDocument();
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
      expect.objectContaining({ credentials: "include", method: "POST" }),
    );
    expect(window.sessionStorage.getItem("lecturepilot.loginSession")).toBeNull();
    expect(window.localStorage.getItem("lecturepilot.loginSession")).not.toContain(
      "signed-test-token",
    );
  });

  it("opens the app before course synchronization and refreshes the profile in place", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/auth/login")) {
        return Promise.resolve(
          jsonResponse({
            username: "student01",
            display_name: null,
            email: null,
            term: "Sommer 2026",
            tenant_id: "tenant-tuebingen",
            account_type: "student",
            roles: ["student"],
            csrf_token: "csrf-token-with-at-least-thirty-two-characters",
            courses: [],
            university_courses: [],
            university_course_sync_status: "loading",
          }),
        );
      }
      if (url.endsWith("/me")) {
        return Promise.resolve(
          jsonResponse({
            username: "student01",
            display_name: "Student Example",
            email: "student01@uni-tuebingen.de",
            tenant_id: "tenant-tuebingen",
            account_type: "student",
            roles: ["student"],
            courses: [],
            university_courses: [],
            university_course_sync_status: "ready",
          }),
        );
      }
      return Promise.resolve(jsonResponse([]));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    await logIn(user);

    expect(await screen.findByRole("status")).toHaveTextContent(/loading your university courses/i);
    expect(
      await screen.findByRole("heading", { name: /welcome, student example/i }),
    ).toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith("/me"))).toBe(true);
  });

  it("lands a non-student Alma account in the professor workspace", async () => {
    const user = userEvent.setup();
    const professorAccount = {
      username: "alma-professor",
      email: "alma-professor@example.edu",
      term: "Sommer 2026",
      tenant_id: "tenant-tuebingen",
      account_type: "professor",
      university_role: "dozent",
      roles: ["professor"],
      courses: [],
    };
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        if (String(input).endsWith("/auth/login")) {
          return Promise.resolve(
            jsonResponse(
              {
                ...professorAccount,
                csrf_token: "csrf-token-with-at-least-thirty-two-characters",
                university_courses: [],
                university_course_sync_status: "loading",
              },
              200,
            ),
          );
        }
        if (String(input).endsWith("/me")) {
          return Promise.resolve(
            jsonResponse(
              {
                ...professorAccount,
                university_courses: [
                  {
                    source: "ilias",
                    external_course_id: "crs:1234",
                    term: "Sommer 2026",
                    title: "Advanced Systems",
                  },
                  {
                    source: "alma",
                    external_course_id: "title:other-course",
                    term: "Sommer 2026",
                    title: "Other Alma Course",
                  },
                ],
                university_course_sync_status: "ready",
              },
              200,
            ),
          );
        }
        return Promise.resolve(jsonResponse([]));
      }),
    );
    render(<App />);

    await user.type(screen.getByLabelText(/zdv username/i), "alma-professor");
    await user.type(screen.getByLabelText(/^password$/i), "university-password");
    await user.click(screen.getByRole("button", { name: /continue with uni tübingen/i }));

    expect(
      await screen.findByRole("navigation", { name: /professor workspace navigation/i }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("navigation", { name: /student workspace navigation/i }),
    ).not.toBeInTheDocument();
    expect(
      await screen.findByRole("navigation", { name: /course builder progress/i }),
    ).toBeInTheDocument();
    expect(
      await screen.findByRole("option", { name: "Advanced Systems" }, { timeout: 2_000 }),
    ).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Other Alma Course" })).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText(/choose from alma or ilias/i), "Advanced Systems");

    expect(screen.getByLabelText(/course name/i)).toHaveValue("Advanced Systems");
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
    await user.click(screen.getByRole("button", { name: /workspaces/i }));
    expect(screen.getByRole("heading", { name: /course workspaces/i })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /open profile/i }));

    await user.click(screen.getByRole("button", { name: /log out/i }));

    expect(screen.getByRole("heading", { name: /welcome to lecturepilot/i })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /course workspaces/i })).not.toBeInTheDocument();
  });

  it("keeps tutor model authority on the server", async () => {
    const user = userEvent.setup();
    const fetchMock = mockLoginAndTutorFetch();
    vi.stubGlobal("fetch", fetchMock);
    renderPublishedApp();

    await logIn(user);
    await openLecture03FromDashboard(user);
    await user.click(screen.getByLabelText(/open tutor chat/i));
    await user.type(screen.getByPlaceholderText(/ask about this lecture/i), "Test fast model.");
    await user.click(screen.getByRole("button", { name: /send message/i }));

    await screen.findByText(/Bayes answer from the tutor/i);
    const agentCall = fetchMock.mock.calls.find(([url]) => String(url).includes("/agent/turn"));
    expect(agentCall?.[1]?.credentials).toBe("include");
    expect(new Headers(agentCall?.[1]?.headers).has("authorization")).toBe(false);
    expect(JSON.parse(String(agentCall?.[1]?.body))).not.toHaveProperty("model");
  });

  it("opens a local demo workspace without submitting credentials", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    await user.click(screen.getByRole("button", { name: /preview local demo/i }));

    expect(
      screen.getByRole("heading", { name: /welcome, demo student/i, level: 1 }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: /grundlagen des maschinellen lernens/i, level: 1 }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /course workspaces/i })).toBeInTheDocument();
    expect(screen.getByText(/not supported yet/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /open lecture 03/i })).not.toBeInTheDocument();
    expect(
      fetchMock.mock.calls.filter(([url]) => String(url).includes("/canvas/publication")),
    ).toHaveLength(3);
    const publicationCall = fetchMock.mock.calls.find(([url]) =>
      String(url).includes("/canvas/publication"),
    );
    expect(new Headers(publicationCall?.[1]?.headers).get("x-user-id")).toBe("local-demo");
  });

  it("opens plain-language project information from the footer", async () => {
    const user = userEvent.setup();
    render(<App />);

    const footer = screen.getByRole("contentinfo");
    expect(footer).toHaveTextContent("Built with ♥ in Tübingen");
    expect(within(footer).getByRole("img", { name: "love" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /how it works/i }));

    expect(
      await screen.findByRole("heading", { name: /how lecturepilot actually works/i }),
    ).toBeInTheDocument();
    expect(screen.getByText("agent harness")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /each student gets a private layer on top/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/shared course truth, separate learner work/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /learn how to learn/i }));

    expect(
      await screen.findByRole("heading", { name: /^learning how to learn$/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/most of us arrive at university/i)).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /sources and further reading/i }),
    ).toBeInTheDocument();
    expect(screen.queryByText(/tübingen contributor/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/current tübingen project/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/broader evidence/i)).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /privacy/i }));

    expect(await screen.findByRole("heading", { name: /privacy notice/i })).toBeInTheDocument();
    expect(
      screen.getByText(/provider keys and model routing stay on the backend/i),
    ).toBeInTheDocument();
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
    expect(
      within(outline).getByRole("button", { name: /ch3\/spam-dall-e.jpg/i }),
    ).toBeInTheDocument();
    expect(within(outline).queryByRole("button", { name: /^formula$/i })).not.toBeInTheDocument();
    expect(
      within(outline).getByRole("group", {
        name: /decision making under uncertainty related items/i,
      }),
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

    expect(
      screen.queryByRole("heading", { name: /course source packet/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /bayes formula and conditional probability/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /ch3\/spam-dall-e.jpg/i })).toBeInTheDocument();
    expect(document.querySelector(".canvas-math .katex")).not.toBeNull();
    expect(document.querySelectorAll(".katex").length).toBeGreaterThan(1);
    expect(screen.getAllByText(/lecture03-eng\.tex/i).length).toBeGreaterThan(0);

    await user.click(screen.getByLabelText(/open document outline/i));
    const outline = screen.getByRole("navigation", { name: /lesson document outline/i });

    expect(
      within(outline).queryByRole("button", { name: /course source packet/i }),
    ).not.toBeInTheDocument();

    await user.click(
      within(outline).getByRole("button", { name: /bayes formula and conditional probability/i }),
    );

    expect(
      screen.getByRole("region", { name: /bayes formula and conditional probability/i }),
    ).toHaveAttribute("aria-current", "true");
  });

  it("renders imported lecture sections in the lesson canvas", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", mockLoginFetch({ published: true }));
    renderPublishedApp();

    await logIn(user);
    await openLecture03FromDashboard(user);

    expect(
      screen.getByRole("region", { name: /bayes rule for classification/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole("region", { name: /naive bayes spam filter/i })).toBeInTheDocument();
    expect(
      screen.getByRole("region", { name: /losses, risks, and reject decisions/i }),
    ).toBeInTheDocument();
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
    expect(
      screen.getByRole("region", { name: /bayes formula and conditional probability/i }),
    ).toHaveAttribute("aria-current", "true");
    const agentRequest = JSON.parse(String(fetchMock.mock.calls.at(-1)?.[1]?.body));
    expect(agentRequest).not.toHaveProperty("user_id");
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

function renderPublishedApp() {
  render(<App />);
}

function jsonResponse(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
