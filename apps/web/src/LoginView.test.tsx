import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { LoginView } from "./LoginView";

describe("LoginView", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows an active loading state during slow live login", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => undefined)));

    render(
      <LoginView
        onLogin={vi.fn()}
        onOpenDemo={vi.fn()}
        onOpenProfessorDemo={vi.fn()}
      />,
    );

    await user.type(screen.getByLabelText(/zdv username/i), "student01");
    await user.type(screen.getByLabelText(/^password$/i), "secret");
    await user.click(screen.getByRole("button", { name: /connect to tue api/i }));

    expect(screen.getByRole("button", { name: /connecting/i })).toBeDisabled();
    expect(screen.getByRole("status")).toHaveTextContent(/loading your alma courses/i);
    expect(screen.getByRole("button", { name: /preview local demo/i })).toBeDisabled();
  });
});
