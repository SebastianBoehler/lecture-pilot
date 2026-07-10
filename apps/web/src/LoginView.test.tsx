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

  it("does not render demo entry points when development access is disabled", () => {
    renderWithI18n(
      <LoginView
        onLogin={vi.fn()}
        onOpenDemo={vi.fn()}
        onOpenProfessorDemo={vi.fn()}
        showDemoAccess={false}
      />,
    );

    expect(screen.queryByRole("button", { name: /preview local demo/i })).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /preview professor account/i }),
    ).not.toBeInTheDocument();
  });

  it("registers a separate pending professor account", async () => {
    const user = userEvent.setup();
    const onLogin = vi.fn();
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          username: "Professor Ada Lovelace",
          email: "ada@example.edu",
          term: "Sommer 2026",
          tenant_id: "tenant-tuebingen",
          account_type: "professor",
          roles: [],
          professor_status: "pending",
          csrf_token: "csrf-token-with-at-least-thirty-two-characters",
          courses: [],
        }),
        { status: 201, headers: { "Content-Type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    renderWithI18n(
      <LoginView
        onLogin={onLogin}
        onOpenDemo={vi.fn()}
        onOpenProfessorDemo={vi.fn()}
        showDemoAccess={false}
      />,
    );

    await user.click(screen.getByRole("tab", { name: /professor/i }));
    await user.click(screen.getByRole("button", { name: /create account/i }));
    await user.type(screen.getByLabelText(/full name/i), "Professor Ada Lovelace");
    await user.type(screen.getByLabelText(/^email$/i), "ada@example.edu");
    await user.type(screen.getByLabelText(/^password$/i), "correct horse battery staple");
    await user.type(screen.getByLabelText(/confirm password/i), "correct horse battery staple");
    await user.click(screen.getByRole("button", { name: /create professor account/i }));

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringMatching(/\/auth\/professor\/register$/),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          display_name: "Professor Ada Lovelace",
          email: "ada@example.edu",
          password: "correct horse battery staple",
        }),
      }),
    );
    expect(onLogin).toHaveBeenCalledWith(
      expect.objectContaining({ account_type: "professor", professor_status: "pending" }),
    );
  });
});
