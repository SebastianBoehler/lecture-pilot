import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import App from "./App";

it("keeps password-reset links usable for an already signed-in professor", async () => {
  const professor = {
    username: "teacher@uni-tuebingen.de",
    account_type: "professor",
    roles: ["professor"],
    auth_transport: "cookie",
    term: "",
    courses: [],
    university_courses: [],
    csrf_token: "a".repeat(32),
  };
  window.localStorage.setItem("lecturepilot.loginSession", JSON.stringify(professor));
  window.history.replaceState(null, "", "/#auth=reset&token=private-reset-token");
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).endsWith("/me")) return Response.json(professor);
      if (String(input).endsWith("/auth/password-reset/confirm")) return Response.json({});
      return Response.json([]);
    }),
  );
  render(<App />);
  expect(screen.getByRole("button", { name: "Set new password" })).toBeInTheDocument();
  await userEvent.type(screen.getByLabelText("LecturePilot password"), "a new separate password");
  await userEvent.click(screen.getByRole("button", { name: "Set new password" }));
  await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("You can now sign in"));
  expect(window.location.hash).toBe("");
  expect(screen.getByLabelText("University email")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /^Sign in$/ })).toBeInTheDocument();
});
