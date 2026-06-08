import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { DEMO_TUTOR_WORKSPACE_STORAGE_KEY } from "./demoTutorWorkspace";
import { mockLoginFetch } from "./testFixtures";

describe("LecturePilot attendance tutor intro", () => {
  beforeEach(() => {
    window.localStorage.setItem(DEMO_TUTOR_WORKSPACE_STORAGE_KEY, "true");
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("seeds the tutor intro from the dashboard attendance choice", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", mockLoginFetch());
    render(<App />);

    await logIn(user);
    const lectureRow = screen.getByRole("heading", { name: /bayesian decision theory/i }).closest("article");
    expect(lectureRow).not.toBeNull();
    await user.click(within(lectureRow as HTMLElement).getByRole("button", { name: "present" }));
    await user.click(screen.getByRole("button", { name: /open lecture 03/i }));
    await user.click(screen.getByLabelText(/open tutor chat/i));

    expect(screen.getByText(/you marked this lecture as attended/i)).toBeInTheDocument();
    expect(screen.getByText("mode: verification")).toBeInTheDocument();
    expect(screen.queryByText(/mark whether you attended/i)).not.toBeInTheDocument();
    expect(screen.queryByText("gate: needs evidence")).not.toBeInTheDocument();
  });
});

async function logIn(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText(/zdv username/i), "student01");
  await user.type(screen.getByLabelText(/^password$/i), "very-secret-password");
  await user.click(screen.getByRole("button", { name: /connect to tue api/i }));
}
