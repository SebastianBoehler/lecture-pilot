import type { PracticeExamAnswer, PracticeExamSolutionQuestion } from "./practiceExamTypes";

export function choiceResult(solution: PracticeExamSolutionQuestion, answer?: PracticeExamAnswer) {
  const multiple = solution.kind === "multiple_select";
  const keys = multiple
    ? (solution.answer_indices ?? [])
    : solution.answer_index === null
      ? []
      : [solution.answer_index];
  const selected = multiple
    ? (answer?.selected_indices ?? [])
    : answer?.selected_index === undefined
      ? []
      : [answer.selected_index];
  const correct =
    selected.length === keys.length &&
    keys.length > 0 &&
    keys.every((index) => selected.includes(index));
  const points = multiple
    ? correct
      ? solution.points
      : -selected.filter((index) => !keys.includes(index)).length
    : correct
      ? solution.points
      : 0;
  return {
    correct,
    points: points === 0 ? 0 : points,
    keys,
    selected,
    unanswered: selected.length === 0,
  };
}
