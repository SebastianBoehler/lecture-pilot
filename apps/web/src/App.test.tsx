import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";

describe("LecturePilot app shell", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("starts with a TUE API wrapper login form", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: /sign in with uni tübingen/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/zdv username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /available lectures/i })).not.toBeInTheDocument();
  });

  it("logs in through the local backend and shows authenticated courses", async () => {
    const user = userEvent.setup();
    const fetchMock = mockLoginFetch();
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    await logIn(user);

    expect(await screen.findByText(/connected as student01/i)).toBeInTheDocument();
    expect(screen.getByText(/machine learning/i)).toBeInTheDocument();
    expect(screen.queryByText("very-secret-password")).not.toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/auth/login",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("opens a local demo workspace without submitting credentials", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    await user.click(screen.getByRole("button", { name: /preview local demo/i }));

    expect(screen.getByText(/connected as local-demo/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /available lectures/i })).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("opens a focused lesson workspace without showing the course dashboard", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", mockLoginFetch());
    render(<App />);

    await logIn(user);
    await user.click(screen.getByRole("button", { name: /open lecture 03/i }));

    expect(screen.getByRole("heading", { name: /kernels and feature maps/i })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /available lectures/i })).not.toBeInTheDocument();
    expect(screen.getByLabelText(/open tutor chat/i)).toBeInTheDocument();
    expect(screen.queryByPlaceholderText(/ask about this lecture/i)).not.toBeInTheDocument();
  });

  it("switches the focused workspace rail between tutor, artifacts, and notes", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", mockLoginFetch());
    render(<App />);

    await logIn(user);
    await user.click(screen.getByRole("button", { name: /open lecture 03/i }));
    await user.click(screen.getByLabelText(/open tutor chat/i));

    expect(screen.getByPlaceholderText(/ask about this lecture/i)).toBeInTheDocument();

    await user.click(screen.getByLabelText(/open artifacts panel/i));

    expect(screen.getByRole("heading", { name: /artifact index/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /jump to micro quiz/i })).toBeInTheDocument();
    expect(screen.queryByPlaceholderText(/ask about this lecture/i)).not.toBeInTheDocument();

    await user.click(screen.getByLabelText(/open lecture notes panel/i));

    expect(screen.getByRole("heading", { name: /source notes/i })).toBeInTheDocument();
    expect(screen.getByText(/official latex source/i)).toBeInTheDocument();
  });

  it("renders visual and interactive demo artifacts", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", mockLoginFetch());
    render(<App />);

    await logIn(user);
    await user.click(screen.getByRole("button", { name: /open lecture 03/i }));

    expect(screen.getByRole("heading", { name: /generated summary/i })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /feature map diagram/i })).toBeInTheDocument();
    expect(screen.getByText(/rbfKernel/)).toBeInTheDocument();
    expect(screen.getByRole("group", { name: /kernel playground/i })).toBeInTheDocument();
    expect(screen.getByText(/balanced local similarity/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /wide kernel/i }));

    expect(screen.getByText(/smooth boundary/i)).toBeInTheDocument();

    await user.click(screen.getByLabelText(/open artifacts panel/i));
    await user.click(screen.getByRole("button", { name: /jump to feature map diagram/i }));

    expect(screen.getByRole("region", { name: /feature map diagram/i })).toHaveAttribute(
      "aria-current",
      "true",
    );
  });

  it("renders learning goals and skill checks in the lesson canvas", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", mockLoginFetch());
    render(<App />);

    await logIn(user);
    await user.click(screen.getByRole("button", { name: /open lecture 03/i }));

    expect(screen.getByRole("region", { name: /learning goals/i })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: /skill check/i })).toBeInTheDocument();
  });

  it("toggles dark mode with a document theme attribute", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: /switch to dark mode/i }));

    expect(document.documentElement.dataset.theme).toBe("dark");
  });

  it("sends a tutor message and applies canvas focus commands", async () => {
    const user = userEvent.setup();
    const fetchMock = mockLoginAndTutorFetch();
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    await logIn(user);
    await user.click(screen.getByRole("button", { name: /open lecture 03/i }));
    await user.click(screen.getByLabelText(/open tutor chat/i));
    await user.type(screen.getByPlaceholderText(/ask about this lecture/i), "What are the goals?");
    await user.click(screen.getByRole("button", { name: /send message/i }));

    expect(await screen.findByText(/learning-goal answer/i)).toBeInTheDocument();
    expect(screen.getByText("focus: learning-goals")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: /learning goals/i })).toHaveAttribute(
      "aria-current",
      "true",
    );
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/agent/turn",
      expect.objectContaining({ method: "POST" }),
    );
  });
});

async function logIn(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText(/zdv username/i), "student01");
  await user.type(screen.getByLabelText(/^password$/i), "very-secret-password");
  await user.click(screen.getByRole("button", { name: /connect to tue api/i }));
}

function mockLoginFetch() {
  return vi.fn().mockResolvedValue({
    ok: true,
    json: async () => loginPayload(),
  });
}

function mockLoginAndTutorFetch() {
  return vi.fn(async (url: string) => {
    if (url.endsWith("/auth/login")) {
      return {
        ok: true,
        json: async () => loginPayload(),
      };
    }

    return {
      ok: true,
      json: async () => ({
        message: "Learning-goal answer from the tutor.",
        canvas_commands: [{ type: "focus_section", section_id: "learning-goals" }],
        artifacts: [],
        model: "openrouter/z-ai/glm-5.1",
        created_at: "2026-06-05T20:00:00Z",
      }),
    };
  });
}

function loginPayload() {
  return {
    username: "student01",
    term: "Sommer 2026",
    courses: [
      {
        id: "alma-machine-learning",
        title: "Machine Learning",
        professor: "Department of Computer Science",
        term: "Sommer 2026",
      },
    ],
  };
}
