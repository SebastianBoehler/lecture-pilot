import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

import App from "./App";

it("continues to a shared join link after signing in from it", async () => {
  const user = userEvent.setup();
  window.history.replaceState({}, "", "/join/medvis/secret-code");
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) =>
      String(url).includes("/join/medvis/secret-code")
        ? Response.json({ course_id: "medvis", title: "MedVis", term: "WS", lecture_count: 3 })
        : Response.json([]),
    ),
  );
  render(<App />);

  await user.click(
    await screen.findByRole("button", { name: /sign in with your lecturepilot account/i }),
  );
  await user.click(await screen.findByRole("button", { name: /view local demo/i }));

  await waitFor(() => expect(window.location.pathname).toBe("/join/medvis/secret-code"));
});

it("forgets a pending destination on explicit logout", async () => {
  const { rememberReturnPath, takeReturnPath } = await import("./shell/returnPath");
  const user = userEvent.setup();
  window.history.replaceState({}, "", "/profile");
  window.localStorage.setItem(
    "lecturepilot.loginSession",
    JSON.stringify({ username: "local-demo", term: "2026", courses: [], roles: ["student"] }),
  );
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => Response.json([])),
  );
  render(<App />);
  rememberReturnPath("/join/medvis/secret-code");

  await user.click(await screen.findByRole("button", { name: /log out/i }));

  expect(takeReturnPath()).toBeNull();
});
