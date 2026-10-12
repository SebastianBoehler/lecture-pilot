import { expect, it } from "vitest";

import { reviewCalendar } from "./reviewCalendar";
import type { GateReviewQueueItem } from "./reviewQueueTypes";

it("exports a private calendar event with an opaque stable identity and overdue time", async () => {
  const item: GateReviewQueueItem = {
    kind: "gate_review",
    id: "review-id",
    course_id: "private-course",
    lecture_id: "lecture-01",
    lecture_title: "Private lecture",
    section_id: "section-1",
    section_title: "Private assessment",
    gate_id: "gate-1",
    gate_revision: "revision-1",
    due_at: "2026-09-20T10:00:00Z",
  };
  const calendar = await reviewCalendar([item], new Date("2026-09-28T08:00:00Z"));
  expect(calendar).toContain("DTSTART:20260928T080000Z\r\n");
  expect(calendar).toContain("DTEND:20260928T081500Z\r\n");
  expect(calendar).toContain("SUMMARY:LecturePilot review");
  expect(calendar).not.toContain("Private");
  expect(calendar).not.toContain("private-course");
  expect(calendar).not.toContain("gate-1");
  expect(calendar.replace(/\r\n /g, "")).toMatch(/UID:[a-f0-9]{64}@lecturepilot/);
});
