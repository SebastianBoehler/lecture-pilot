import { afterEach, describe, expect, it, vi } from "vitest";

import { landingView, resolveLandingView } from "./appLanding";
import type { LoginSession } from "./types";

const student: LoginSession = {
  username: "student01",
  term: "Sommer 2026",
  account_type: "student",
  roles: ["student"],
  courses: [],
};
const professor: LoginSession = {
  username: "prof01",
  term: "Sommer 2026",
  account_type: "professor",
  roles: ["professor"],
  courses: [],
};

function stubWorkspaces(payload: unknown, status = 200) {
  const fetchMock = vi.fn(
    async (_input: RequestInfo | URL) => new Response(JSON.stringify(payload), { status }),
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("landing view", () => {
  it("keeps signed-out visitors and students on their own landing views", async () => {
    expect(landingView(null)).toBe("login");
    expect(await resolveLandingView(student)).toBe("dashboard");
  });

  it("sends a professor without courses to the course builder", async () => {
    const fetchMock = stubWorkspaces([]);

    expect(await resolveLandingView(professor)).toBe("professor");
    expect(String(fetchMock.mock.calls[0][0])).toContain("/admin/courses");
  });

  it("sends a professor with existing courses to course management", async () => {
    stubWorkspaces([{ course: { id: "ml", title: "ML" }, lectures: [] }]);

    expect(await resolveLandingView(professor)).toBe("course-management");
  });

  it("shows course management when the course list cannot be read", async () => {
    stubWorkspaces({ detail: "Unavailable" }, 503);

    expect(await resolveLandingView(professor)).toBe("course-management");
  });

  it("lands professors without course-management rights on their profile", async () => {
    const fetchMock = stubWorkspaces([]);

    expect(await resolveLandingView({ ...professor, roles: [] })).toBe("profile");
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
