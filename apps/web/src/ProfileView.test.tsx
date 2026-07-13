import { screen } from "@testing-library/react";
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
        session={session}
      />,
    );

    expect(screen.getByText("lecturer")).toBeInTheDocument();
    expect(screen.getByText("Daniel Example")).toBeInTheDocument();
    expect(screen.getByText("professor@example.edu")).toBeInTheDocument();
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

    renderWithI18n(<ProfileView session={session} />);

    expect(screen.getByText("LecturePilot courses")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Your LecturePilot workspaces" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Your LecturePilot workspaces are loading.")).toBeInTheDocument();
  });
});
