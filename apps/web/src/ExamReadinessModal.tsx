import { RotateCcw, X } from "lucide-react";
import { useLayoutEffect, useRef } from "react";

import { ExamQuestionStep } from "./ExamQuestionStep";
import { answeredQuestionCount, isQuestionAnswered } from "./examReadinessState";
import type { ExamAnswerMap } from "./examReadinessState";
import { ExamReadinessResult } from "./ExamReadinessResult";
import { useI18n } from "./i18n";
import type {
  ExamReadinessAttemptResult,
  ExamReadinessCheck,
  ExamReadinessQuestion,
  Lecture,
  UniversityCourse,
} from "./types";

export function ExamReadinessModal({
  activeQuestion,
  answers,
  check,
  course,
  error,
  lectures,
  loading,
  result,
  submitting,
  onAnswer,
  onBack,
  onClose,
  onNext,
  onOpenLecture,
  onRestart,
  onSubmit,
}: {
  activeQuestion: number;
  answers: ExamAnswerMap;
  check: ExamReadinessCheck | null;
  course: UniversityCourse;
  error: string | null;
  lectures: Lecture[];
  loading: boolean;
  result: ExamReadinessAttemptResult | null;
  submitting: boolean;
  onAnswer: (question: ExamReadinessQuestion, answer: number | string) => void;
  onBack: () => void;
  onClose: () => void;
  onNext: () => void;
  onOpenLecture: (lecture: Lecture) => void;
  onRestart: () => void;
  onSubmit: () => void;
}) {
  const { t } = useI18n();
  const dialogRef = useRef<HTMLDialogElement>(null);
  const titleId = `exam-readiness-title-${course.id}`;
  const descriptionId = `exam-readiness-description-${course.id}`;
  const question = check?.questions[activeQuestion];
  const isLastQuestion = Boolean(check && activeQuestion === check.questions.length - 1);

  useLayoutEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (typeof dialog.showModal === "function") dialog.showModal();
    else dialog.setAttribute("open", "");
    return () => {
      if (typeof dialog.close === "function" && dialog.open) dialog.close();
    };
  }, []);

  return (
    <dialog
      aria-describedby={descriptionId}
      aria-labelledby={titleId}
      aria-modal="true"
      className="exam-modal"
      ref={dialogRef}
      role="dialog"
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onKeyDown={(event) => {
        if (event.key === "Escape" && typeof dialogRef.current?.showModal !== "function") onClose();
      }}
    >
      <header className="exam-modal-header">
        <div>
          <h2 id={titleId}>{t("exam.title")}</h2>
          <p id={descriptionId}>{course.title}</p>
        </div>
        <div className="exam-modal-actions">
          {check ? (
            <button disabled={loading} type="button" onClick={onRestart}>
              <RotateCcw aria-hidden="true" size={15} />
              {result ? t("exam.newSample") : t("exam.restart")}
            </button>
          ) : null}
          <button aria-label={t("exam.close")} type="button" onClick={onClose}>
            <X aria-hidden="true" size={18} />
          </button>
        </div>
      </header>

      {error && check ? <p className="form-error exam-modal-error">{error}</p> : null}
      {loading && !check ? (
        <p className="exam-modal-loading" role="status">
          {t("exam.preparingStatus")}
        </p>
      ) : null}
      {error && !check && !loading ? (
        <section className="exam-modal-empty" role="alert">
          <strong>{t("exam.prepareError.title")}</strong>
          <p>{error}</p>
          <button type="button" onClick={onRestart}>
            {t("exam.tryAgain")}
          </button>
        </section>
      ) : null}
      {check && !question ? (
        <section className="exam-modal-empty" role="status">
          <strong>{t("exam.empty.title")}</strong>
          <p>{t("exam.empty.help")}</p>
        </section>
      ) : null}

      {check && question && !result ? (
        <>
          <div className="exam-step-progress" aria-live="polite">
            <div>
              <strong>
                {t("exam.question.position", {
                  current: activeQuestion + 1,
                  total: check.questions.length,
                })}
              </strong>
              <span>{t("exam.publishedCount", { count: check.published_lecture_count })}</span>
            </div>
            <progress
              aria-label={t("exam.progressLabel")}
              max={check.questions.length}
              value={activeQuestion + 1}
            />
          </div>
          <section className="exam-modal-body" aria-label={t("exam.question.sectionLabel")}>
            <ExamQuestionStep
              answer={answers[question.id]}
              question={question}
              onAnswer={(answer) => onAnswer(question, answer)}
            />
          </section>
          <footer className="exam-modal-footer">
            <button disabled={activeQuestion === 0} type="button" onClick={onBack}>
              {t("exam.back")}
            </button>
            <span>
              {t("exam.answered", {
                answered: answeredQuestionCount(check, answers),
                total: check.questions.length,
              })}
            </span>
            {isLastQuestion ? (
              <button
                className="exam-primary-action"
                disabled={!allQuestionsAnswered(check, answers) || submitting}
                type="button"
                onClick={onSubmit}
              >
                {submitting ? t("exam.checking") : t("exam.checkReadiness")}
              </button>
            ) : (
              <button
                className="exam-primary-action"
                disabled={!isQuestionAnswered(question, answers[question.id])}
                type="button"
                onClick={onNext}
              >
                {t("exam.nextQuestion")}
              </button>
            )}
          </footer>
        </>
      ) : null}

      {result && check ? (
        <section
          className="exam-modal-body exam-result-body"
          aria-label={t("exam.result.sectionLabel")}
        >
          <ExamReadinessResult
            check={check}
            lectures={lectures}
            result={result}
            onOpenLecture={onOpenLecture}
          />
        </section>
      ) : null}
    </dialog>
  );
}

function allQuestionsAnswered(check: ExamReadinessCheck, answers: ExamAnswerMap) {
  return check.questions.every((item) => isQuestionAnswered(item, answers[item.id]));
}
