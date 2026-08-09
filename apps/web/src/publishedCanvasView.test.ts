import { describe, expect, it } from "vitest";

import {
  isPublishedCanvasView,
  reconcileCanvasLearnerState,
  type PublishedCanvasView,
} from "./publishedCanvasView";
import type { LearnerLessonState } from "./learnerLessonStateTypes";
import { canvasPayload } from "./testCanvasFixture";
import type { CanvasDocument } from "./types";

describe("published canvas view", () => {
  it("keeps the rendered canvas version authoritative when learner state is newer", () => {
    const view = publishedView(1);
    const newerState = learnerState(2);

    expect(reconcileCanvasLearnerState(view, newerState)).toEqual({
      publicationVersion: 1,
      quizStates: {},
      currentLearnerState: null,
      requiresReconciliation: true,
    });
  });

  it("applies quiz locks only when learner state matches the rendered canvas", () => {
    const view = publishedView(2);
    const currentState = learnerState(2);

    expect(reconcileCanvasLearnerState(view, currentState)).toEqual({
      publicationVersion: 2,
      quizStates: currentState.quiz_states,
      currentLearnerState: currentState,
      requiresReconciliation: false,
    });
  });

  it("rejects incomplete or unversioned canvas responses", () => {
    const view = publishedView(1);

    expect(isPublishedCanvasView(view, "martius-ml", "lecture-03")).toBe(true);
    expect(
      isPublishedCanvasView({ ...view, publication_version: 0 }, "martius-ml", "lecture-03"),
    ).toBe(false);
    expect(
      isPublishedCanvasView({ ...view, learning_map_revision: "" }, "martius-ml", "lecture-03"),
    ).toBe(false);
    expect(isPublishedCanvasView(view, "other-course", "lecture-03")).toBe(false);
  });
});

function publishedView(publicationVersion: number): PublishedCanvasView {
  return {
    document: canvasPayload() as CanvasDocument,
    publication_version: publicationVersion,
    learning_map_revision: "a".repeat(64),
  };
}

function learnerState(publicationVersion: number): LearnerLessonState {
  return {
    course_id: "martius-ml",
    lecture_id: "lecture-03",
    publication_version: publicationVersion,
    gate_statuses: {},
    quiz_states: {
      "losses-and-risks-quiz": {
        selected_index: 1,
        correct: true,
        publication_version: publicationVersion,
        attempt_index: 1,
        first_attempt_correct: true,
        latest_outcome: "correct",
        correction_state: "not_needed",
      },
    },
    active_session_goal: null,
    pending_check: null,
    due_gate_reviews: [],
  };
}
