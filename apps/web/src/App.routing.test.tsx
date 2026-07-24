import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

import App from "./App";
import { mockLoginFetch } from "./testFixtures";

it("uses the browser history across several page transitions", async () => {
  const user = userEvent.setup();
  vi.stubGlobal("fetch", mockLoginFetch());
  render(<App />);

  await logIn(user);
  expect(window.location.pathname).toBe("/workspaces");

  await user.click(screen.getByRole("button", { name: /open profile/i }));
  expect(window.location.pathname).toBe("/profile");

  await user.click(screen.getByRole("button", { name: /privacy/i }));
  expect(window.location.pathname).toBe("/privacy");

  window.history.back();
  await waitFor(() => expect(window.location.pathname).toBe("/profile"));
  expect(screen.getByRole("heading", { name: /profile/i })).toBeInTheDocument();

  window.history.back();
  await waitFor(() => expect(window.location.pathname).toBe("/workspaces"));
  expect(screen.getByRole("heading", { name: /course workspaces/i })).toBeInTheDocument();
});

it("opens public information directly from its URL", async () => {
  window.history.replaceState({}, "", "/how-it-works");
  render(<App />);

  expect(
    await screen.findByRole("heading", { name: /how lecturepilot actually works/i }),
  ).toBeInTheDocument();
});

it("puts the routed page into feedback diagnostics", async () => {
  const user = userEvent.setup();
  vi.stubGlobal("fetch", mockLoginFetch());
  render(<App />);

  await logIn(user);
  await user.click(screen.getByRole("button", { name: /open profile/i }));
  await user.click(screen.getByRole("button", { name: /send feedback/i }));

  const mailto = screen.getByRole("link", { name: /open email draft/i }).getAttribute("href") ?? "";
  expect(decodeURIComponent(mailto)).toContain(`Page: ${window.location.origin}/profile`);
});

async function logIn(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText(/zdv username/i), "student01");
  await user.type(screen.getByLabelText(/^password$/i), "very-secret-password");
  await user.click(screen.getByRole("button", { name: /continue with uni tübingen/i }));
  await screen.findByRole("heading", { name: /course workspaces/i });
}
