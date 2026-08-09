import { describe, expect, it } from "vitest";

import { StaleQuizPublicationError, quizAnswerPayload, quizSubmissionError } from "./analyticsApi";
import { isLearnerLessonState } from "./learnerLessonStateApi";

describe("quiz publication contract", () => {
  it("requires learner lesson state to carry a positive publication version", () => {
    const state = {
      course_id: "course-1",
      lecture_id: "lecture-1",
      publication_version: 3,
      gate_statuses: {},
      quiz_states: {},
      active_session_goal: null,
      pending_check: null,
      due_gate_reviews: [],
    };

    expect(isLearnerLessonState(state, "course-1", "lecture-1")).toBe(true);
    expect(
      isLearnerLessonState({ ...state, publication_version: undefined }, "course-1", "lecture-1"),
    ).toBe(false);
    expect(
      isLearnerLessonState({ ...state, publication_version: 0 }, "course-1", "lecture-1"),
    ).toBe(false);
  });

  it("sends the captured publication version and recognizes only the typed stale response", () => {
    expect(
      quizAnswerPayload({
        attendance: "present",
        attemptId: "attempt-123",
        blockId: "risk-quiz",
        optionIndex: 1,
        publicationVersion: 3,
      }),
    ).toEqual({
      attendance: "present",
      attempt_id: "attempt-123",
      block_id: "risk-quiz",
      option_index: 1,
      publication_version: 3,
    });

    const error = quizSubmissionError(409, {
      detail: {
        code: "stale_quiz_publication",
        message: "This quiz belongs to an older publication. Reload the lecture.",
      },
    });
    expect(error).toBeInstanceOf(StaleQuizPublicationError);
    expect(error.message).toBe("This quiz belongs to an older publication. Reload the lecture.");
  });
});
