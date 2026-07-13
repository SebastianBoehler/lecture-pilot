import type { ExamReadinessAnswer, ExamReadinessCheck, ExamReadinessQuestion } from "./types";

export type ExamAnswerMap = Record<string, number | string>;

export function isQuestionAnswered(
  question: ExamReadinessQuestion,
  answer: number | string | undefined,
) {
  return question.kind === "multiple_choice"
    ? typeof answer === "number"
    : String(answer ?? "").trim().length > 0;
}

export function answersForCheck(
  check: ExamReadinessCheck,
  answers: ExamAnswerMap,
): ExamReadinessAnswer[] {
  return check.questions.map((question) => {
    const answer = answers[question.id];
    if (question.kind === "multiple_choice") {
      return { question_id: question.id, selected_index: Number(answer) };
    }
    return { question_id: question.id, text: String(answer ?? "").trim() };
  });
}

export function answeredQuestionCount(check: ExamReadinessCheck, answers: ExamAnswerMap) {
  return check.questions.filter((question) => isQuestionAnswered(question, answers[question.id]))
    .length;
}
