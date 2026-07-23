import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

import App from "./App";
import { FEEDBACK_TURN_THRESHOLD, feedbackPromptStorageKey } from "./useFeedbackPrompt";
import { mockLoginFetch } from "./testFixtures";

it("shows the feedback entry point only after sign-in", async () => {
  const user = userEvent.setup();
  vi.stubGlobal("fetch", mockLoginFetch());
  render(<App />);

  expect(screen.queryByRole("button", { name: /send feedback/i })).not.toBeInTheDocument();
  await logIn(user);

  await screen.findByRole("heading", { name: /welcome, student example/i });
  await user.click(screen.getByRole("button", { name: /send feedback/i }));
  expect(screen.getByRole("dialog", { name: /send feedback/i })).toBeInTheDocument();
});

it("shows a qualified student's prompt on a later dashboard visit", async () => {
  vi.stubGlobal("fetch", mockLoginFetch());
  window.localStorage.setItem(
    "lecturepilot.loginSession",
    JSON.stringify({
      account_type: "student",
      auth_transport: "cookie",
      courses: [],
      roles: ["student"],
      term: "Sommer 2026",
      university_course_sync_status: "ready",
      username: "student01",
    }),
  );
  window.localStorage.setItem(
    feedbackPromptStorageKey("student01"),
    JSON.stringify({
      prompted: false,
      qualifiedVisitId: "earlier-page-visit",
      successfulTurns: FEEDBACK_TURN_THRESHOLD,
    }),
  );
  render(<App />);

  const dialog = await screen.findByRole("dialog", { name: /help us improve lecturepilot/i });
  expect(dialog).toHaveTextContent(/you have now tried the tutor/i);
});

async function logIn(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText(/zdv username/i), "student01");
  await user.type(screen.getByLabelText(/^password$/i), "very-secret-password");
  await user.click(screen.getByRole("button", { name: /continue with uni tübingen/i }));
}
