import { afterEach, describe, expect, it, vi } from "vitest";

import { refreshSession } from "./sessionApi";
import type { LoginSession } from "../shared/types";

describe("refreshSession", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("refreshes the account without dropping the login CSRF token", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        json: async () => ({
          username: "student01",
          display_name: "Student Example",
          csrf_token: null,
          courses: [],
          university_courses: [],
        }),
      })),
    );
    const session: LoginSession = {
      username: "student01",
      term: "Sommer 2026",
      auth_transport: "cookie",
      csrf_token: "csrf-token-with-at-least-thirty-two-characters",
      courses: [],
    };

    const refreshed = await refreshSession(session);

    expect(refreshed.display_name).toBe("Student Example");
    expect(refreshed.csrf_token).toBe(session.csrf_token);
    expect(refreshed.term).toBe("Sommer 2026");
  });
});
