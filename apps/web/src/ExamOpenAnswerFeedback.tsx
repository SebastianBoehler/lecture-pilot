import { useI18n } from "./i18n";
import type { ExamReadinessCheck, ExamReadinessQuestionResult } from "./types";

export function ExamOpenAnswerFeedback({
  check,
  results,
}: {
  check: ExamReadinessCheck;
  results: ExamReadinessQuestionResult[];
}) {
  const { t } = useI18n();
  const feedback = results.flatMap((result) => {
    if (
      result.answer_kind !== "open_ended" ||
      result.status !== "evaluated" ||
      result.score == null ||
      !result.feedback
    ) {
      return [];
    }
    const question = check.questions.find((item) => item.id === result.question_id);
    return question ? [{ feedback: result.feedback, question, score: result.score }] : [];
  });

  if (!feedback.length) return null;

  return (
    <section
      className="exam-open-answer-feedback"
      aria-labelledby="exam-open-answer-feedback-title"
    >
      <header>
        <h4 id="exam-open-answer-feedback-title">{t("exam.feedback.title")}</h4>
      </header>
      <ol>
        {feedback.map((item) => (
          <li key={item.question.id}>
            <span className="exam-open-answer-score">{Math.round(item.score * 100)}%</span>
            <div>
              <h5>{item.question.section_title}</h5>
              <small>{item.question.lecture_title}</small>
              <p>{item.feedback}</p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
