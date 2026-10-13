import { describe, expect, it } from "vitest";

import { courseLectureSummary, isLectureBusy, lectureStatus } from "./courseLectureStatus";
import type { LectureState } from "./courseLectureStateTypes";

const base: LectureState = {
  lecture_id: "lecture-01",
  number: "01",
  title: "Introduction",
  date: "2026-10-01",
  published: true,
  published_at: "2026-10-02T10:00:00Z",
  sources: "current",
  goals: "approved",
  draft: "published",
  draft_error: null,
  next_action: "none",
};

describe("lectureStatus", () => {
  it.each([
    [{}, "published", "success"],
    [{ draft: "generating", next_action: "wait" }, "generating", "progress"],
    [{ goals: "proposing", next_action: "wait" }, "proposing", "progress"],
    [{ draft: "failed", next_action: "retry_draft" }, "failed", "danger"],
    [{ draft: "ready", next_action: "review_draft" }, "draft_ready", "attention"],
    [{ next_action: "confirm_routing" }, "routing", "attention"],
    [{ goals: "needs_review", next_action: "review_goals" }, "goals_review", "attention"],
    [{ goals: "missing", next_action: "review_goals" }, "goals_review", "attention"],
    [
      { goals: "stale", sources: "changed", next_action: "keep_or_regenerate_goals" },
      "sources_changed",
      "attention",
    ],
    [
      { published: false, draft: "none", next_action: "generate_draft" },
      "draft_needed",
      "attention",
    ],
    [{ published: false, draft: "none" }, "not_published", "neutral"],
  ] as const)("derives %o as %s", (patch, kind, tone) => {
    expect(lectureStatus({ ...base, ...patch })).toEqual({ kind, tone });
  });

  it("prefers running work over older failures", () => {
    expect(lectureStatus({ ...base, goals: "proposing", draft: "failed" }).kind).toBe("proposing");
  });
});

describe("isLectureBusy", () => {
  it("is true only while goals are proposed or a draft is generated", () => {
    expect(isLectureBusy(base)).toBe(false);
    expect(isLectureBusy({ ...base, goals: "proposing" })).toBe(true);
    expect(isLectureBusy({ ...base, draft: "generating" })).toBe(true);
    expect(isLectureBusy({ ...base, next_action: "wait" })).toBe(true);
  });
});

describe("courseLectureSummary", () => {
  it("counts published lectures and lectures that need the professor", () => {
    expect(
      courseLectureSummary([
        base,
        { ...base, lecture_id: "b", next_action: "review_draft", draft: "ready" },
        { ...base, lecture_id: "c", published: false, next_action: "wait", goals: "proposing" },
      ]),
    ).toEqual({ total: 3, published: 2, needsReview: 1, readyToPublish: 1 });
  });
});
