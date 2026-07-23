import { screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ProfileView } from "./ProfileView";
import { renderWithI18n } from "./test/renderWithI18n";
import type { LoginSession } from "./types";

describe("ProfileView", () => {
  it("shows the Alma role without a separate professor approval flow", () => {
    const session: LoginSession = {
      username: "alma-professor",
      display_name: "Daniel Example",
      email: "professor@example.edu",
      term: "Sommer 2026",
      tenant_id: "tenant-tuebingen",
      account_type: "professor",
      university_role: "lecturer",
      roles: ["professor"],
      auth_transport: "cookie",
      csrf_token: "csrf-token-with-at-least-thirty-two-characters",
      courses: [],
    };

    renderWithI18n(
      <ProfileView
        learnerProfileState={{
          profile: null,
          loading: false,
          error: "Student workspace access is required.",
          saveCalibration: async () => {},
          removePreference: async () => {},
          clearMemory: async () => {},
          refresh: async () => {},
        }}
        onLogout={() => undefined}
        session={session}
      />,
    );

    const account = screen.getByRole("region", { name: "Account" });
    expect(screen.getByRole("heading", { level: 1, name: "Profile" })).toBeInTheDocument();
    expect(within(account).getByText("lecturer")).toBeInTheDocument();
    expect(within(account).getByText("Daniel Example")).toBeInTheDocument();
    expect(within(account).getByText("professor@example.edu")).toBeInTheDocument();
    expect(within(account).getByText("alma-professor")).toBeInTheDocument();
    expect(screen.queryByText(/professor access/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/student workspace access is required/i)).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /request professor approval/i }),
    ).not.toBeInTheDocument();
  });

  it("distinguishes pending university data from joined LecturePilot workspaces", () => {
    const session: LoginSession = {
      username: "student01",
      term: "Sommer 2026",
      account_type: "student",
      roles: ["student"],
      courses: [],
      university_course_sync_status: "loading",
    };

    renderWithI18n(<ProfileView onLogout={() => undefined} session={session} />);

    expect(
      within(screen.getByRole("region", { name: "Account" })).getByText("Workspaces"),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Workspaces" })).toBeInTheDocument();
    expect(screen.getByText("Your workspaces are loading.")).toBeInTheDocument();
  });
});
