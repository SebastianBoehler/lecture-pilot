import { afterEach, describe, expect, it, vi } from "vitest";

import {
  approvePracticeDesign,
  getPracticeDesign,
  proposePracticeDesign,
  updatePracticeDesign,
} from "./practiceDesignApi";
import type { PracticeDesign, PracticeDesignUpdate } from "./practiceDesignTypes";
import { practiceDesignFixture } from "./practiceDesignTestFixtures";
import type { LoginSession } from "../shared/types";

const session: LoginSession = {
  access_token: "professor-token",
  courses: [],
  roles: ["professor"],
  term: "Summer 2026",
  username: "professor-a",
};

describe("practice-design API", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("uses the exact authenticated routes and revision-bound bodies", async () => {
    const fetchMock = vi.fn<typeof fetch>(async (input) =>
      String(input).endsWith("/intent/findings") ? response([]) : response(design()),
    );
    vi.stubGlobal("fetch", fetchMock);
    const current = design();
    const calls = () =>
      fetchMock.mock.calls.filter(([input]) => !String(input).endsWith("/intent/findings"));

    await getPracticeDesign({ courseId: "course-1", lectureId: "lecture-01", session });
    await proposePracticeDesign({
      courseId: "course-1",
      lectureId: "lecture-01",
      refresh: true,
      session,
    });
    await updatePracticeDesign({
      courseId: "course-1",
      lectureId: "lecture-01",
      session,
      update: update(current),
    });
    await approvePracticeDesign({
      courseId: "course-1",
      lectureId: "lecture-01",
      design: current,
      intent: { fixed_target_ids: ["posterior"] },
      session,
    });

    const [get, propose, put, approve] = calls();
    expect(String(get[0])).toMatch(
      /\/admin\/courses\/course-1\/lectures\/lecture-01\/practice-design$/,
    );
    expect(new Headers(get[1]?.headers).get("Authorization")).toBe("Bearer professor-token");
    expect(String(propose[0])).toMatch(/\/practice-design\/intent\/proposal\?refresh=true$/);
    expect(propose[1]?.method).toBe("POST");
    expect(String(put[0])).toMatch(/\/practice-design\/intent$/);
    expect(put[1]?.method).toBe("PUT");
    const { targets: _targets, ...goals } = update(current);
    expect(JSON.parse(String(put[1]?.body))).toEqual(goals);
    expect(String(approve[0])).toMatch(/\/practice-design\/intent\/approve$/);
    expect(JSON.parse(String(approve[1]?.body))).toEqual({
      fixed_target_ids: ["posterior"],
      source_revision: current.source_revision,
      practice_design_revision: current.revision,
    });
  });

  it("preserves server error details and status, including stale conflicts", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        response({ detail: "The practice design or source revision changed. Reload it." }, 409),
      ),
    );

    await expect(
      approvePracticeDesign({
        courseId: "course-1",
        lectureId: "lecture-01",
        design: design(),
        intent: { fixed_target_ids: [] },
        session,
      }),
    ).rejects.toMatchObject({
      message: "The practice design or source revision changed. Reload it.",
      status: 409,
    });
  });
});

function design(): PracticeDesign {
  return practiceDesignFixture({ lectureId: "lecture-01", reviewSeverity: null });
}

function update(current: PracticeDesign): PracticeDesignUpdate {
  return {
    goals: current.learning_intent.goals,
    source_revision: current.source_revision,
    practice_design_revision: current.revision,
    lecture_title: current.lecture_title,
    objective: current.objective,
    planning_context: current.planning_context,
    targets: current.targets,
  };
}

function response(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
