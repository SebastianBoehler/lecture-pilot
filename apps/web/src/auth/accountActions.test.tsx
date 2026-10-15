import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { LoginView } from "./LoginView";
import { renderWithI18n } from "../test/renderWithI18n";

const props = {
  onLogin: vi.fn(),
  onOpenDemo: vi.fn(),
  onOpenProfessorDemo: vi.fn(),
  showDemoAccess: false,
};
afterEach(() => {
  vi.unstubAllGlobals();
  window.history.replaceState(null, "", "/");
});

it("registers university email with a separate password and shows email instructions", async () => {
  const user = userEvent.setup();
  const fetchMock = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);
  renderWithI18n(<LoginView {...props} />);
  await user.click(screen.getByRole("button", { name: "Create account" }));
  await user.type(screen.getByLabelText("University email"), "student@uni-tuebingen.de");
  const password = screen.getByLabelText("LecturePilot password");
  expect(password).toHaveAttribute("autocomplete", "new-password");
  expect(password).toHaveAttribute("minlength", "12");
  await user.type(password, "a separate password");
  await user.click(screen.getByRole("button", { name: "Create account" }));
  await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Check your inbox"));
  expect(fetchMock.mock.calls[0][0]).toContain("/auth/register");
  expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
    email: "student@uni-tuebingen.de",
    password: "a separate password",
  });
});

it("requires explicit confirmation of a verification link and removes its token after success", async () => {
  window.history.replaceState(null, "", "/#auth=verify&token=private-token");
  const fetchMock = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);
  renderWithI18n(<LoginView {...props} />);
  expect(fetchMock).not.toHaveBeenCalled();
  await userEvent.click(screen.getByRole("button", { name: "Verify email" }));
  await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("You can now sign in"));
  expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ token: "private-token" });
  expect(window.location.hash).toBe("");
});

it("shows delivery errors during password recovery", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ detail: "Email could not be sent." }), { status: 503 }),
      ),
  );
  renderWithI18n(<LoginView {...props} />);
  await userEvent.click(screen.getByRole("button", { name: "Forgot password?" }));
  await userEvent.type(screen.getByLabelText("University email"), "student@uni-tuebingen.de");
  expect(screen.queryByLabelText("LecturePilot password")).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Forgot password?" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Email could not be sent.");
});
