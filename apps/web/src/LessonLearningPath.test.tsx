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

  it("opens a student learning path tab and jumps to concepts", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", mockLoginFetch({ published: true }));
    render(<App />);

    await logIn(user);
    await openLecture03FromDashboard(user);
    await user.click(screen.getByLabelText(/open learning path/i));

    const panel = await screen.findByRole("complementary", { name: /learning path panel/i });
    expect(within(panel).getByRole("heading", { name: /learning path/i })).toBeInTheDocument();
    const path = within(panel).getByRole("list", {
      name: /bayesian decision theory learning path/i,
    });
    const currentStep = within(path).getByRole("button", {
      name: /decision making under uncertainty.*current/i,
    });
    expect(currentStep).toHaveAttribute("aria-pressed", "true");
    expect(currentStep).toHaveAttribute("aria-current", "step");
    const firstBranch = currentStep.closest("li")?.querySelector(":scope > .student-path-branch");
    expect(firstBranch).toBeInTheDocument();
    expect(
      within(firstBranch as HTMLElement).getByRole("button", {
        name: /bayes formula and conditional probability/i,
      }),
    ).toBeInTheDocument();
    expect(within(path).getAllByText(/bayesian decision theory/i)).not.toHaveLength(0);
    expect(within(path).getAllByText(/^quiz$/i)).toHaveLength(2);

    await user.click(
      within(path).getByRole("button", {
        name: /bayes formula and conditional probability.*available/i,
      }),
    );

    await waitFor(() => {
      expect(
        screen.getByRole("region", { name: /bayes formula and conditional probability/i }),
      ).toHaveAttribute("aria-current", "true");
    });
    expect(
      within(path).getByRole("button", {
        name: /decision making under uncertainty.*available/i,
      }),
    ).not.toHaveTextContent(/visited/i);
  });
});

async function logIn(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText(/zdv username/i), "student01");
  await user.type(screen.getByLabelText(/^password$/i), "very-secret-password");
  await user.click(screen.getByRole("button", { name: /continue with uni tübingen/i }));
}
