import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ProfileView } from "./ProfileView";
import { renderWithI18n } from "./test/renderWithI18n";
import type { LoginSession } from "./types";

const adminSession: LoginSession = {
  username: "platform-admin",
  email: "admin@example.edu",
  term: "Sommer 2026",
  tenant_id: "tenant-tuebingen",
  account_type: "student",
  roles: ["student", "tenant_admin"],
  auth_transport: "cookie",
  csrf_token: "csrf-token-with-at-least-thirty-two-characters",
  courses: [],
};

describe("ProfileView professor approvals", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("lets a platform administrator approve a pending professor account", async () => {
    const user = userEvent.setup();
    let pending = true;
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/approve") && init?.method === "POST") {
        pending = false;
        return Promise.resolve(jsonResponse({ status: "approved" }));
      }
      if (url.endsWith("/platform/professor-requests")) {
        return Promise.resolve(
          jsonResponse(
            pending
              ? [
                  {
                    id: "8ce79d24-3909-4210-b4ac-a793b30ccf65",
                    user_id: "c4f0786e-aaca-4e59-bd93-6889205bc51b",
                    username: "Professor Ada Lovelace",
                    email: "ada@example.edu",
                    university_role: "lecturer",
                    university_available_roles: ["lecturer", "examiner"],
                    status: "pending",
                    requested_at: "2026-07-10T12:00:00Z",
                  },
                ]
              : [],
          ),
        );
      }
      return Promise.resolve(jsonResponse({ detail: "Unexpected request" }, 500));
    });
    vi.stubGlobal("fetch", fetchMock);

    renderWithI18n(
      <ProfileView
        session={adminSession}
        onBack={vi.fn()}
        onSessionChange={vi.fn()}
      />,
    );

    expect(await screen.findByText("Professor Ada Lovelace")).toBeInTheDocument();
    expect(screen.getByText("ada@example.edu")).toBeInTheDocument();
    expect(screen.getByText("Alma role: lecturer")).toBeInTheDocument();
    expect(screen.getByText("Available Alma roles: lecturer, examiner")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /^approve$/i }));

    expect(await screen.findByText(/no pending requests/i)).toBeInTheDocument();
    const approvalCall = fetchMock.mock.calls.find(([url]) => String(url).includes("/approve"));
    expect(new Headers(approvalCall?.[1]?.headers).get("x-csrf-token")).toBe(
      adminSession.csrf_token,
    );
  });
});

function jsonResponse(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
