import { describe, expect, it } from "vitest";
import { choiceResult } from "./practiceExamScoring";
import type { PracticeExamSolutionQuestion } from "./practiceExamTypes";

const solution: PracticeExamSolutionQuestion = {
  id: "q-1",
  kind: "multiple_select",
  points: 4,
  answer_index: null,
  answer_indices: [0, 2],
  reference_answer: null,
  rubric: [],
};

describe("multiple-answer practice scoring", () => {
  it.each([
    [[], 0, false],
    [[0], 0, false],
    [[0, 2], 4, true],
    [[0, 1], -1, false],
    [[1, 3], -2, false],
    [[0, 1, 2, 3], -2, false],
  ])("scores selected options %j", (selected, points, correct) => {
    expect(choiceResult(solution, { selected_indices: selected })).toMatchObject({
      points,
      correct,
    });
  });
  it("preserves single-answer scoring and distinguishes unanswered from index zero", () => {
    const single = {
      ...solution,
      kind: "multiple_choice" as const,
      answer_index: 0,
      answer_indices: [],
    };
    expect(choiceResult(single, {}).points).toBe(0);
    expect(choiceResult(single, { selected_index: 0 })).toMatchObject({ points: 4, correct: true });
    expect(choiceResult(single, { selected_index: 1 })).toMatchObject({
      points: 0,
      correct: false,
    });
  });
});
