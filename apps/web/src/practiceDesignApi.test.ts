import { afterEach, describe, expect, it, vi } from "vitest";

import {
  approvePracticeDesign,
  getPracticeDesign,
  proposePracticeDesign,
  updatePracticeDesign,
} from "./practiceDesignApi";
import type { PracticeDesign, PracticeDesignUpdate } from "./practiceDesignTypes";
import type { LoginSession } from "./types";

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
    const fetchMock = vi.fn<typeof fetch>(async (_input, _init) => response(design()));
    vi.stubGlobal("fetch", fetchMock);
    const current = design();

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
      session,
    });

    expect(String(fetchMock.mock.calls[0][0])).toMatch(
      /\/admin\/courses\/course-1\/lectures\/lecture-01\/practice-design$/,
    );
    expect(new Headers(fetchMock.mock.calls[0][1]?.headers).get("Authorization")).toBe(
      "Bearer professor-token",
    );
    expect(String(fetchMock.mock.calls[1][0])).toMatch(/\/proposal\?refresh=true$/);
    expect(fetchMock.mock.calls[1][1]?.method).toBe("POST");
    expect(fetchMock.mock.calls[2][1]?.method).toBe("PUT");
    expect(JSON.parse(String(fetchMock.mock.calls[2][1]?.body))).toEqual(update(current));
    expect(fetchMock.mock.calls[3][1]?.method).toBe("POST");
    expect(JSON.parse(String(fetchMock.mock.calls[3][1]?.body))).toEqual({
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
        session,
      }),
    ).rejects.toMatchObject({
      message: "The practice design or source revision changed. Reload it.",
      status: 409,
    });
  });
});

function design(): PracticeDesign {
  return {
    schema_version: 1,
    course_id: "course-1",
    lecture_id: "lecture-01",
    lecture_title: "Bayes rule",
    objective: "Calculate a posterior from evidence.",
    source_revision: "s".repeat(64),
    revision: "d".repeat(64),
    approval: null,
    targets: [
      {
        id: "posterior",
        title: "Posterior",
        outcome: "Calculate a posterior from evidence.",
        baseline_task: "Calculate the posterior.",
        independent_exit_task: "Calculate another posterior.",
        delayed_transfer_task: "Calculate a diagnostic posterior.",
        evidence_criteria: [
          { id: "substitute", description: "Uses stated values.", required: true },
        ],
        misconceptions: [],
        hint_ladder: [],
        review_after_days: 7,
        source_refs: ["Lecture01.md"],
      },
    ],
  };
}

function update(current: PracticeDesign): PracticeDesignUpdate {
  return {
    source_revision: current.source_revision,
    practice_design_revision: current.revision,
    lecture_title: current.lecture_title,
    objective: current.objective,
    targets: current.targets,
  };
}

function response(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
