import { describe, expect, it } from "vitest";

import { lectureSnapshot } from "./performanceMetrics";

describe("lectureSnapshot", () => {
  it("labels missing learner activity as no data rather than a warning state", () => {
    expect(lectureSnapshot(lecture(), null)).toMatchObject({
      events: 0,
      gateRate: "n/a",
      quizRate: "n/a",
      status: "no-data",
    });
  });
});

function lecture() {
  return {
    attendance: "unknown" as const,
    date: "2026-05-09",
    id: "lecture-01",
    number: "01",
    title: "Introduction",
  };
}
