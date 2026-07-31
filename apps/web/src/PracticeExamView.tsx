import { useState } from "react";

import { useI18n } from "./i18n";
import { downloadPracticeExamPdf } from "./practiceExamApi";
import { readPracticeExamDraft, savePracticeExamDraft } from "./practiceExamDraft";
import type { PracticeExam, PracticeExamAnswers } from "./practiceExamTypes";
import type { LoginSession } from "./types";

export function PracticeExamView({
  courseId,
  exam,
  session,
  onClose,
}: {
  courseId: string;
  exam: PracticeExam;
  session: LoginSession;
  onClose: () => void;
}) {
  const { t } = useI18n();
  const [answers, setAnswers] = useState<PracticeExamAnswers>(() =>
    readPracticeExamDraft(session.username, courseId, exam.id),
  );
  const [pdfBusy, setPdfBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function answer(questionId: string, value: PracticeExamAnswers[string]) {
    const next = { ...answers, [questionId]: value };
    setAnswers(next);
    savePracticeExamDraft(session.username, courseId, exam.id, next);
  }

  async function downloadPdf() {
    setPdfBusy(true);
    setError(null);
    try {
      const blob = await downloadPracticeExamPdf(courseId, exam.id, session);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `practice-exam-${exam.id.slice(0, 8)}.pdf`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : t("practice.pdfFailed"));
    } finally {
      setPdfBusy(false);
    }
  }

  return (
    <dialog
      aria-labelledby="practice-exam-view-title"
      className="practice-exam-dialog practice-exam-view"
      open
    >
      <header>
        <div>
          <p>
            {t("practice.view.eyebrow", {
              minutes: exam.duration_minutes,
              points: exam.total_points,
            })}
          </p>
          <h2 id="practice-exam-view-title">{exam.title}</h2>
        </div>
        <div className="practice-exam-view-actions">
          <button disabled={pdfBusy} type="button" onClick={() => void downloadPdf()}>
            {pdfBusy ? t("practice.pdfPreparing") : t("practice.pdf")}
          </button>
          <button aria-label={t("practice.closeDialog")} type="button" onClick={onClose}>
            ×
          </button>
        </div>
      </header>
      <div className="practice-exam-dialog-body">
        {error ? (
          <p className="practice-exam-error" role="alert">
            {error}
          </p>
        ) : null}
        <div className="practice-exam-instructions">
          {exam.instructions.map((instruction) => (
            <p key={instruction}>{instruction}</p>
          ))}
          <p>{t("practice.view.localDraft")}</p>
        </div>
        <ol className="practice-question-list">
          {exam.questions.map((question, index) => (
            <li key={question.id}>
              <fieldset>
                <legend>
                  <span>{t("practice.question", { number: index + 1 })}</span>
                  {question.prompt}
                </legend>
                <span className="practice-question-points">
                  {t("practice.points", { count: question.points })}
                </span>
                {question.kind === "multiple_choice" ? (
                  question.options.map((option, optionIndex) => (
                    <label key={option}>
                      <input
                        checked={answers[question.id]?.selected_index === optionIndex}
                        name={question.id}
                        type="radio"
                        onChange={() => answer(question.id, { selected_index: optionIndex })}
                      />
                      <span>{option}</span>
                    </label>
                  ))
                ) : (
                  <label>
                    <span className="sr-only">
                      {t("practice.answerLabel", { number: index + 1 })}
                    </span>
                    <textarea
                      aria-label={t("practice.answerLabel", { number: index + 1 })}
                      rows={6}
                      value={answers[question.id]?.text ?? ""}
                      onChange={(event) => answer(question.id, { text: event.currentTarget.value })}
                    />
                  </label>
                )}
              </fieldset>
            </li>
          ))}
        </ol>
      </div>
      <footer>
        <button type="button" onClick={onClose}>
          {t("practice.closeExam")}
        </button>
      </footer>
    </dialog>
  );
}
