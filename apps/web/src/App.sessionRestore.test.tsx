import { render, screen, waitFor } from "@testing-library/react";
import { expect, it, vi } from "vitest";

import App from "./App";
import { mockLoginFetch } from "./testFixtures";
import type { LoginSession } from "./types";

const storedSession: LoginSession = {
  username: "student01",
  display_name: "Student Example",
  email: "student01@uni-tuebingen.de",
  term: "Sommer 2026",
  tenant_id: "tenant-tuebingen",
  account_type: "student",
  roles: ["student"],
  auth_transport: "cookie",
  csrf_token: "csrf-token-with-at-least-thirty-two-characters",
  courses: [
    {
      id: "martius-ml",
      title: "Grundlagen des Maschinellen Lernens",
      professor: "Prof. Georg Martius",
      term: "Sommer 2026",
    },
  ],
  university_courses: [],
  university_course_sync_status: "ready",
};

it("clears an expired persisted session before rendering a protected route", async () => {
  window.localStorage.setItem("lecturepilot.loginSession", JSON.stringify(storedSession));
  window.history.replaceState({}, "", "/profile");
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).endsWith("/me")) {
        return json({ detail: "Session cookie or bearer token is required." }, 401);
      }
      return json([]);
    }),
  );

  render(<App />);

  expect(
    await screen.findByRole("heading", { name: /sign in to lecturepilot/i }),
  ).toBeInTheDocument();
  expect(window.localStorage.getItem("lecturepilot.loginSession")).toBeNull();
  expect(window.location.pathname).toBe("/");
});

it("restores a canvas session without loading learner-profile data", async () => {
  window.localStorage.setItem("lecturepilot.loginSession", JSON.stringify(storedSession));
  window.history.replaceState({}, "", "/courses/martius-ml/lectures/lecture-03");
  const appFetch = mockLoginFetch({ published: true });
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.endsWith("/me")) return json(accountPayload());
    return appFetch(url, init);
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);

  expect(await screen.findByLabelText(/close tutor chat/i)).toBeInTheDocument();
  await waitFor(() => {
    expect(
      fetchMock.mock.calls.filter(([input]) => String(input).endsWith("/me/learning-profile")),
    ).toHaveLength(0);
  });
});

function accountPayload() {
  const {
    auth_transport: _authTransport,
    csrf_token: _csrfToken,
    term: _term,
    ...account
  } = storedSession;
  return account;
}

function json(payload: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => payload,
  };
}
