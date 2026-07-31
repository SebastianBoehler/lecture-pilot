import { useState } from "react";

import { useI18n } from "./i18n";
import { MathText } from "./MathText";
import { loadPracticeExamSolutions } from "./practiceExamApi";
import { savePracticeExamPdf, savePracticeExamSolutionPdf } from "./practiceExamDownload";
import { readPracticeExamDraft, savePracticeExamDraft } from "./practiceExamDraft";
import type {
  PracticeExam,
  PracticeExamAnswers,
  PracticeExamSolutionSheet,
} from "./practiceExamTypes";
import { PracticeExamSolutionSheet as SolutionSheetView } from "./PracticeExamSolutionSheet";
import type { LoginSession } from "./types";
import { useModalDialog } from "./useModalDialog";

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
  const [reviewBusy, setReviewBusy] = useState(false);
  const [solutions, setSolutions] = useState<PracticeExamSolutionSheet | null>(null);
  const [solutionPdfBusy, setSolutionPdfBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dialogRef = useModalDialog();

  function answer(questionId: string, value: PracticeExamAnswers[string]) {
    const next = { ...answers, [questionId]: value };
    setAnswers(next);
    savePracticeExamDraft(session.username, courseId, exam.id, next);
  }

  async function downloadPdf() {
    setPdfBusy(true);
    setError(null);
    try {
      await savePracticeExamPdf(courseId, exam.id, session);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : t("practice.pdfFailed"));
    } finally {
      setPdfBusy(false);
    }
  }

  async function finishAndReview() {
    setReviewBusy(true);
    setError(null);
    try {
      setSolutions(await loadPracticeExamSolutions(courseId, exam.id, session));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : t("practice.solutions.loadFailed"));
    } finally {
      setReviewBusy(false);
    }
  }

  async function downloadSolutionPdf() {
    setSolutionPdfBusy(true);
    setError(null);
    try {
      await savePracticeExamSolutionPdf(courseId, exam.id, session);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : t("practice.solutions.pdfFailed"));
    } finally {
      setSolutionPdfBusy(false);
    }
  }

  return (
    <dialog
      aria-labelledby="practice-exam-view-title"
      aria-modal="true"
      className="practice-exam-dialog practice-exam-view"
      ref={dialogRef}
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
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
          {solutions ? (
            <button
              disabled={solutionPdfBusy}
              type="button"
              onClick={() => void downloadSolutionPdf()}
            >
              {solutionPdfBusy ? t("practice.solutions.pdfPreparing") : t("practice.solutions.pdf")}
            </button>
          ) : (
            <button disabled={pdfBusy} type="button" onClick={() => void downloadPdf()}>
              {pdfBusy ? t("practice.pdfPreparing") : t("practice.pdf")}
            </button>
          )}
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
        {solutions ? (
          <SolutionSheetView answers={answers} exam={exam} solutions={solutions} />
        ) : (
          <>
            <div className="practice-exam-instructions">
              {exam.instructions.map((instruction) => (
                <p key={instruction}>
                  <MathText highlightedText={null} text={instruction} />
                </p>
              ))}
              <div
                aria-labelledby="practice-exam-privacy-title"
                className="practice-exam-privacy"
                role="note"
              >
                <div>
                  <strong id="practice-exam-privacy-title">{t("practice.privacy.title")}</strong>
                  <p>{t("practice.view.localDraft")}</p>
                </div>
              </div>
            </div>
            <ol className="practice-question-list">
              {exam.questions.map((question, index) => (
                <li key={question.id}>
                  <fieldset>
                    <legend>
                      <span aria-hidden="true" className="practice-question-number">
                        {index + 1}.
                      </span>
                      <span className="practice-question-prompt">
                        <MathText highlightedText={null} text={question.prompt} />
                      </span>
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
                          <span>
                            <MathText highlightedText={null} text={option} />
                          </span>
                        </label>
                      ))
                    ) : (
                      <textarea
                        aria-label={t("practice.answerLabel", { number: index + 1 })}
                        rows={6}
                        value={answers[question.id]?.text ?? ""}
                        onChange={(event) =>
                          answer(question.id, { text: event.currentTarget.value })
                        }
                      />
                    )}
                  </fieldset>
                </li>
              ))}
            </ol>
          </>
        )}
      </div>
      <footer>
        <button type="button" onClick={onClose}>
          {t("practice.closeExam")}
        </button>
        {!solutions ? (
          <button
            className="practice-primary"
            disabled={reviewBusy}
            type="button"
            onClick={() => void finishAndReview()}
          >
            {reviewBusy ? t("practice.solutions.loading") : t("practice.solutions.finish")}
          </button>
        ) : null}
      </footer>
    </dialog>
  );
}
