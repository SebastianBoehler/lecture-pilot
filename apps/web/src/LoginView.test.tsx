import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { LoginView } from "./LoginView";
import { renderWithI18n } from "./test/renderWithI18n";

describe("LoginView", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows an active loading state during slow live login", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn(() => new Promise(() => undefined)),
    );

    renderWithI18n(
      <LoginView onLogin={vi.fn()} onOpenDemo={vi.fn()} onOpenProfessorDemo={vi.fn()} />,
    );

    await user.type(screen.getByLabelText(/zdv username/i), "student01");
    await user.type(screen.getByLabelText(/^password$/i), "secret");
    await user.click(screen.getByRole("button", { name: /continue with uni tübingen/i }));

    expect(screen.getByRole("button", { name: /signing in/i })).toBeDisabled();
    expect(screen.getByRole("status")).toHaveTextContent(/loading your course workspace/i);
    expect(screen.getByRole("button", { name: /preview local demo/i })).toBeDisabled();
  });
});
