import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { openLecture03FromDashboard } from "./testLessonActions";
import { mockLoginFetch } from "./testFixtures";

describe("Lesson learning path", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("combines navigation and practice guidance without separate path or notes tabs", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", mockLoginFetch({ published: true }));
    render(<App />);

    await logIn(user);
    await openLecture03FromDashboard(user);
    expect(screen.queryByLabelText(/open learning path/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/open lecture notes panel/i)).not.toBeInTheDocument();
    await user.click(screen.getByLabelText(/open document outline/i));
    const panel = screen.getByRole("complementary", { name: /document outline panel/i });
    const outline = within(panel).getByRole("navigation", { name: /lesson document outline/i });
    expect(
      within(outline).getByRole("button", { name: "Decision making under uncertainty" }),
    ).toHaveAttribute("aria-pressed", "true");
    await user.click(within(panel).getByText("How practice works"));
    expect(within(panel).getByText(/do not unlock the next section/i)).toBeVisible();
    const next = within(outline).getByRole("button", {
      name: /bayes formula and conditional probability/i,
    });
    expect(next).toBeEnabled();
    await user.click(next);
    await waitFor(() =>
      expect(
        screen.getByRole("region", { name: /bayes formula and conditional probability/i }),
      ).toHaveAttribute("aria-current", "true"),
    );
    expect(next).toHaveAttribute("aria-pressed", "true");
  });
});

async function logIn(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText(/zdv username/i), "student01");
  await user.type(screen.getByLabelText(/^password$/i), "very-secret-password");
  await user.click(screen.getByRole("button", { name: /continue with uni tübingen/i }));
}
