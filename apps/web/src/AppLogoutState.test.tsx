import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import App from "./App";

describe("App logout state", () => {
  it("clears the saved professor builder flow on logout", async () => {
    const user = userEvent.setup();
    window.sessionStorage.setItem(
      "lecturepilot.professor-builder.current",
      JSON.stringify({ courseReady: true }),
    );
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => jsonPayload(url)),
    );

    render(<App />);

    await user.click(screen.getByRole("button", { name: /preview professor account/i }));
    expect(window.sessionStorage.getItem("lecturepilot.professor-builder.current")).not.toBeNull();

    await user.click(screen.getByRole("button", { name: /open profile/i }));
    await user.click(screen.getByRole("button", { name: /log out/i }));

    expect(window.sessionStorage.getItem("lecturepilot.professor-builder.current")).toBeNull();
  });
});

function jsonPayload(url: string) {
  if (url.endsWith("/courses")) return json([]);
  if (url.includes("/canvas/publication")) return json({ published: false });
  return json([]);
}

function json(payload: unknown) {
  return {
    ok: true,
    json: async () => payload,
  };
}
