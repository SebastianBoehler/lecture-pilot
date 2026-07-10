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

  it("exposes stable browser autofill and password-manager field semantics", async () => {
    const user = userEvent.setup();

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
    expect(studentPassword).toHaveAttribute("id", "current-password");
    expect(studentPassword).toHaveAttribute("name", "password");
    expect(studentPassword).toHaveAttribute("autocomplete", "current-password");
    expect(studentPassword.closest("form")).toHaveAttribute("method", "post");

    await user.click(screen.getByRole("tab", { name: /professor/i }));
    const professorEmail = screen.getByLabelText(/^email$/i);
    const professorPassword = screen.getByLabelText(/^password$/i);
    expect(professorEmail).toHaveAttribute("id", "email");
    expect(professorEmail).toHaveAttribute("name", "email");
    expect(professorEmail).toHaveAttribute("type", "email");
    expect(professorEmail).toHaveAttribute("autocomplete", "username");
    expect(professorPassword).toHaveAttribute("id", "current-password");
    expect(professorPassword).toHaveAttribute("autocomplete", "current-password");

    await user.click(screen.getByRole("button", { name: /create account/i }));
    expect(screen.getByLabelText(/full name/i)).toHaveAttribute("autocomplete", "name");
    expect(screen.getByLabelText(/^password$/i)).toHaveAttribute("id", "new-password");
    expect(screen.getByLabelText(/^password$/i)).toHaveAttribute(
      "autocomplete",
      "new-password",
    );
    expect(screen.getByLabelText(/confirm password/i)).toHaveAttribute(
      "autocomplete",
      "new-password",
    );
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
            account_type: "university",
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
    expect(window.localStorage.getItem("lecturepilot.rememberedStudentUsername")).toBe(
      "student01",
    );
    expect([...Array(window.localStorage.length).keys()]
      .map((index) => window.localStorage.getItem(window.localStorage.key(index) ?? ""))
      .join(" "))
      .not.toContain("student-secret");
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

    await user.click(screen.getByRole("tab", { name: /professor/i }));
    await user.click(screen.getByRole("tab", { name: /student/i }));
    expect(screen.getByRole("checkbox", { name: /remember username/i })).not.toBeChecked();
    expect(screen.getByLabelText(/zdv username/i)).toHaveValue("");
  });

  it("restores the last account type and remembered professor email", async () => {
    const user = userEvent.setup();
    window.localStorage.setItem("lecturepilot.loginAudience", "professor");
    window.localStorage.setItem(
      "lecturepilot.rememberedProfessorEmail",
      "professor@example.edu",
    );

    renderWithI18n(
      <LoginView
        onLogin={vi.fn()}
        onOpenDemo={vi.fn()}
        onOpenProfessorDemo={vi.fn()}
        showDemoAccess={false}
      />,
    );

    expect(screen.getByRole("tab", { name: /professor/i })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.getByLabelText(/^email$/i)).toHaveValue("professor@example.edu");
    expect(screen.getByRole("checkbox", { name: /remember email/i })).toBeChecked();

    await user.click(screen.getByRole("tab", { name: /student/i }));
    expect(window.localStorage.getItem("lecturepilot.loginAudience")).toBe("student");
    await user.click(screen.getByRole("tab", { name: /professor/i }));
    await user.click(screen.getByRole("button", { name: /create account/i }));
    expect(screen.queryByRole("checkbox", { name: /remember email/i })).not.toBeInTheDocument();
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
