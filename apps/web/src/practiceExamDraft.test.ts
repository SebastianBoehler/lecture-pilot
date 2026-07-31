import { describe, expect, it } from "vitest";

import {
  clearAllPracticeExamDrafts,
  clearPracticeExamDraft,
  ensurePracticeExamDraftAccount,
  readPracticeExamDraft,
  savePracticeExamDraft,
} from "./practiceExamDraft";

describe("practice exam tab drafts", () => {
  it("separates drafts by account, course, and exam", () => {
    savePracticeExamDraft("student-a", "course-1", "exam-1", {
      "q-01": { selected_index: 2 },
    });
    savePracticeExamDraft("student-a", "course-1", "exam-2", {
      "q-01": { text: "second" },
    });

    expect(readPracticeExamDraft("student-a", "course-1", "exam-1")).toEqual({
      "q-01": { selected_index: 2 },
    });
    expect(readPracticeExamDraft("student-b", "course-1", "exam-1")).toEqual({});
    expect(readPracticeExamDraft("student-a", "course-2", "exam-1")).toEqual({});
  });

  it("clears one deleted exam without clearing another", () => {
    savePracticeExamDraft("student-a", "course-1", "exam-1", { "q-01": { text: "one" } });
    savePracticeExamDraft("student-a", "course-1", "exam-2", { "q-01": { text: "two" } });

    clearPracticeExamDraft("student-a", "course-1", "exam-1");

    expect(readPracticeExamDraft("student-a", "course-1", "exam-1")).toEqual({});
    expect(readPracticeExamDraft("student-a", "course-1", "exam-2")).toEqual({
      "q-01": { text: "two" },
    });
  });

  it("clears all drafts on logout or account change", () => {
    ensurePracticeExamDraftAccount("student-a");
    savePracticeExamDraft("student-a", "course-1", "exam-1", { "q-01": { text: "one" } });
    ensurePracticeExamDraftAccount("student-b");
    expect(readPracticeExamDraft("student-a", "course-1", "exam-1")).toEqual({});

    savePracticeExamDraft("student-b", "course-1", "exam-1", { "q-01": { text: "two" } });
    clearAllPracticeExamDrafts();
    expect(readPracticeExamDraft("student-b", "course-1", "exam-1")).toEqual({});
  });
});
