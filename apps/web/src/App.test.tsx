import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

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
});

