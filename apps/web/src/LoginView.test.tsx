import { screen, waitFor } from "@testing-library/react";
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

  it("keeps university sign-in primary and separates optional previews", () => {
    renderWithI18n(
      <LoginView onLogin={vi.fn()} onOpenDemo={vi.fn()} onOpenProfessorDemo={vi.fn()} />,
    );

    expect(
      screen.getByRole("heading", { level: 1, name: "Sign in to LecturePilot" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Preview without signing in" })).toBeInTheDocument();
    expect(
      screen.getByText(/students and teaching staff use the same ZDV sign-in/i),
    ).toBeInTheDocument();
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
    expect(screen.queryByText(/separate lecturepilot professor/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/^email$/i)).not.toBeInTheDocument();
  });

  it("exposes stable browser autofill and password-manager field semantics", () => {
    renderWithI18n(
      <LoginView
        onLogin={vi.fn()}
        onOpenDemo={vi.fn()}
        onOpenProfessorDemo={vi.fn()}
        showDemoAccess={false}
      />,
    );

    const studentUsername = screen.getByLabelText(/zdv username/i);
    const studentPassword = screen.getByLabelText(/^password$/i);
    expect(studentUsername).toHaveAttribute("id", "username");
    expect(studentUsername).toHaveAttribute("name", "username");
    expect(studentUsername).toHaveAttribute("autocomplete", "username");
    expect(studentUsername).toHaveAttribute("autocapitalize", "none");
    expect(studentUsername).toHaveAttribute("spellcheck", "false");
    expect(studentPassword).toHaveAttribute("id", "university-current-password");
    expect(studentPassword).toHaveAttribute("name", "password");
    expect(studentPassword).toHaveAttribute("autocomplete", "current-password");
    expect(studentPassword.closest("form")).toHaveAttribute("method", "post");
  });

  it("remembers only an opted-in student username after a successful login", async () => {
    const user = userEvent.setup();
    const onLogin = vi.fn();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            username: "student01",
            term: "Sommer 2026",
            tenant_id: "tenant-tuebingen",
            account_type: "student",
            roles: ["student"],
            csrf_token: "csrf-token-with-at-least-thirty-two-characters",
            courses: [],
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );

    renderWithI18n(
      <LoginView
        onLogin={onLogin}
        onOpenDemo={vi.fn()}
        onOpenProfessorDemo={vi.fn()}
        showDemoAccess={false}
      />,
    );

    expect(screen.getByRole("checkbox", { name: /remember username/i })).toBeChecked();
    await user.type(screen.getByLabelText(/zdv username/i), "student01");
    await user.type(screen.getByLabelText(/^password$/i), "student-secret");
    await user.click(screen.getByRole("button", { name: /continue with uni tübingen/i }));

    await waitFor(() => expect(onLogin).toHaveBeenCalledOnce());
    expect(window.localStorage.getItem("lecturepilot.rememberedStudentUsername")).toBe("student01");
    expect(
      [...Array(window.localStorage.length).keys()]
        .map((index) => window.localStorage.getItem(window.localStorage.key(index) ?? ""))
        .join(" "),
    ).not.toContain("student-secret");
  });

  it("prefills and clears a previously remembered student username", async () => {
    const user = userEvent.setup();
    window.localStorage.setItem("lecturepilot.rememberedStudentUsername", "student01");

    renderWithI18n(
      <LoginView
        onLogin={vi.fn()}
        onOpenDemo={vi.fn()}
        onOpenProfessorDemo={vi.fn()}
        showDemoAccess={false}
      />,
    );

    expect(screen.getByLabelText(/zdv username/i)).toHaveValue("student01");
    const remember = screen.getByRole("checkbox", { name: /remember username/i });
    expect(remember).toBeChecked();

    await user.click(remember);

    expect(window.localStorage.getItem("lecturepilot.rememberedStudentUsername")).toBeNull();
    expect(window.localStorage.getItem("lecturepilot.rememberStudentUsernameEnabled")).toBe(
      "false",
    );

    expect(screen.getByRole("checkbox", { name: /remember username/i })).not.toBeChecked();
  });
});
