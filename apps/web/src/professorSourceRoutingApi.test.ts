import { afterEach, describe, expect, it, vi } from "vitest";

import { proposeSourceRouting } from "./professorApi";
import type { LoginSession } from "./types";

describe("professor source-routing API", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("sends an authenticated refresh request when assignments are rebuilt", async () => {
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) =>
      Promise.resolve(
        new Response(
          JSON.stringify({
            confirmed: false,
            course_id: "course-1",
            routes: [],
            source_revision: "a".repeat(64),
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await proposeSourceRouting("course-1", session, true);

    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toMatch(
      /\/admin\/courses\/course-1\/source-routing\/proposal\?refresh=true$/,
    );
    expect(init?.method).toBe("POST");
    expect(new Headers(init?.headers).get("Authorization")).toBe("Bearer professor-token");
  });
});

const session: LoginSession = {
  access_token: "professor-token",
  courses: [],
  roles: ["professor"],
  term: "Summer 2026",
  username: "professor-a",
};
