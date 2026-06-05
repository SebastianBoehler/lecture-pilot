import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import App from "./App";

describe("LecturePilot app shell", () => {
  it("opens a focused lesson workspace without showing the course dashboard", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: /open lecture 03/i }));

    expect(screen.getByRole("heading", { name: /kernels and feature maps/i })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /available lectures/i })).not.toBeInTheDocument();
    expect(screen.getByLabelText(/open tutor drawer/i)).toBeInTheDocument();
    expect(screen.queryByPlaceholderText(/ask about this lecture/i)).not.toBeInTheDocument();
  });

  it("opens the tutor drawer from the focused workspace rail", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: /open lecture 03/i }));
    await user.click(screen.getByLabelText(/open tutor drawer/i));

    expect(screen.getByPlaceholderText(/ask about this lecture/i)).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /quiz/i })).toBeInTheDocument();
  });

  it("toggles dark mode with a document theme attribute", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: /switch to dark mode/i }));

    expect(document.documentElement.dataset.theme).toBe("dark");
  });

  it("sends a tutor message and applies canvas focus commands", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        message: "Kernel-focused answer from the tutor.",
        canvas_commands: [{ type: "focus_section", section_id: "kernel-trick" }],
        artifacts: [],
        model: "openrouter/z-ai/glm-5.1",
        created_at: "2026-06-05T20:00:00Z",
      }),
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    await user.click(screen.getByRole("button", { name: /open lecture 03/i }));
    await user.click(screen.getByLabelText(/open tutor drawer/i));
    await user.type(screen.getByPlaceholderText(/ask about this lecture/i), "Explain the kernel trick");
    await user.click(screen.getByRole("button", { name: /send message/i }));

    expect(await screen.findByText(/kernel-focused answer/i)).toBeInTheDocument();
    expect(screen.getByRole("region", { name: /kernel trick/i })).toHaveAttribute(
      "aria-current",
      "true",
    );
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/agent/turn",
      expect.objectContaining({ method: "POST" }),
    );
  });
});
